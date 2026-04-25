import re
from pathlib import Path

import httpx
from google.adk.tools.tool_context import ToolContext
from lxml import html as lxml_html

BASE_URL = "https://base-donnees-publique.medicaments.gouv.fr/medicament"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _clean(element) -> str:
    """Return normalised text content of an lxml element."""
    return re.sub(r"\s+", " ", element.text_content()).strip()


def _parse_fiche_info(panel) -> dict[str, dict]:
    """Parse the 'fiche info' tab panel.

    Sections are delimited by <h5 id="..."> headings.
    """
    sections: dict[str, dict] = {}
    h5_elements = panel.xpath(".//h5[@id]")
    for idx, h5 in enumerate(h5_elements):
        section_id = h5.get("id")
        titre = _clean(h5)
        content_parts: list[str] = []

        # Collect siblings between this h5 and the next h5
        parent = h5.getparent()
        if parent is None:
            sections[section_id] = {"titre": titre, "niveau": 1, "contenu": ""}
            continue

        children = list(parent)
        h5_index = children.index(h5)
        # Find next h5 index (may be in a different parent; scan forward)
        next_h5_index = None
        if idx + 1 < len(h5_elements):
            next_h5 = h5_elements[idx + 1]
            if next_h5.getparent() is parent:
                next_h5_index = children.index(next_h5)

        end = next_h5_index if next_h5_index is not None else len(children)
        for child in children[h5_index + 1 : end]:
            if not isinstance(child.tag, str):
                continue
            text = _clean(child)
            if text:
                content_parts.append(text)

        sections[section_id] = {
            "titre": titre,
            "niveau": 1,
            "contenu": "\n".join(content_parts),
        }

    return sections


def _parse_rcp(panel) -> dict[str, dict]:
    """Parse the RCP (Résumé des Caractéristiques du Produit) tab panel.

    Headings: <p class="AmmAnnexeTitre1"> (niveau 1) and
              <p class="AmmAnnexeTitre2"> (niveau 2).
    Each heading contains a <span id="SECTION_ID">TITLE</span>.
    """
    sections: dict[str, dict] = {}

    contenu_div = panel.find('.//*[@id="contenu"]')
    if contenu_div is None:
        return sections

    current_id: str | None = None
    current_titre: str = ""
    current_niveau: int = 1
    current_parts: list[str] = []

    def _save_current():
        if current_id is not None:
            sections[current_id] = {
                "titre": current_titre,
                "niveau": current_niveau,
                "contenu": "\n".join(current_parts),
            }

    for child in contenu_div:
        if not isinstance(child.tag, str):  # skip HtmlComment and PIs
            continue
        is_h1 = "AmmAnnexeTitre1" in (child.get("class") or "")
        is_h2 = "AmmAnnexeTitre2" in (child.get("class") or "")
        if is_h1 or is_h2:
            _save_current()
            niveau = 1 if is_h1 else 2
            span = child.find('.//span[@id]')
            if span is not None:
                current_id = span.get("id")
                current_titre = _clean(span)
            else:
                current_id = f"section_{len(sections)}"
                current_titre = _clean(child)
            current_niveau = niveau
            current_parts = []
        else:
            text = _clean(child)
            if text:
                current_parts.append(text)

    _save_current()
    return sections


def _parse_notice(panel) -> dict[str, dict]:
    """Parse the patient notice tab panel.

    The sidebar links identify section ids; the actual content spans mark
    where each section starts in the document.
    """
    sections: dict[str, dict] = {}

    # Collect sidebar links: <a class="fr-sidemenu__link" href="#SECTION_ID">
    sidebar_links = panel.xpath('.//*[contains(@class, "fr-sidemenu__link")]')
    sidebar_ids: list[str] = []
    id_to_titre: dict[str, str] = {}

    for a in sidebar_links:
        href = a.get("href", "")
        if href.startswith("#"):
            sid = href[1:]
            sidebar_ids.append(sid)
            id_to_titre[sid] = _clean(a)

    sidebar_id_set = set(sidebar_ids)

    for idx, section_id in enumerate(sidebar_ids):
        titre = id_to_titre[section_id]
        content_parts: list[str] = []

        # Find the span with this id
        span = panel.find(f'.//*[@id="{section_id}"]')
        if span is None:
            sections[section_id] = {"titre": titre, "niveau": 1, "contenu": ""}
            continue

        # Walk up: span -> <a name="..."> -> heading <p> -> content container
        a_name = span.getparent()
        if a_name is None:
            sections[section_id] = {"titre": titre, "niveau": 1, "contenu": ""}
            continue
        heading_p = a_name.getparent()
        if heading_p is None:
            sections[section_id] = {"titre": titre, "niveau": 1, "contenu": ""}
            continue
        container = heading_p.getparent()
        if container is None:
            sections[section_id] = {"titre": titre, "niveau": 1, "contenu": ""}
            continue

        children = list(container)
        try:
            heading_idx = children.index(heading_p)
        except ValueError:
            sections[section_id] = {"titre": titre, "niveau": 1, "contenu": ""}
            continue

        for child in children[heading_idx + 1 :]:
            if not isinstance(child.tag, str):
                continue
            # Stop if we find a span whose id is in sidebar_ids
            found_stop = False
            for descendant_span in child.iter("span"):
                if descendant_span.get("id") in sidebar_id_set:
                    found_stop = True
                    break
            if found_stop:
                break
            text = _clean(child)
            if text:
                content_parts.append(text)

        sections[section_id] = {
            "titre": titre,
            "niveau": 1,
            "contenu": "\n".join(content_parts),
        }

    return sections


def _parse_bon_usage(panel) -> dict[str, dict]:
    """Parse the 'bon usage' tab panel — flat text extraction."""
    return {
        "bon-usage": {
            "titre": "Documents de bon usage",
            "niveau": 1,
            "contenu": _clean(panel),
        }
    }


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------


async def fetch_medication_doc(cis: str, tool_context: ToolContext) -> dict:
    """Downloads and parses the official medication file (base-donnees-publique.medicaments.gouv.fr).

    Args:
        cis: CIS code (unique identifier) of the medication.

    Returns:
        Table of contents indexed by tab (rcp, notice, fiche-info, bon-usage)
        without text content — use read_section to read a section.
    """
    url = f"{BASE_URL}/{cis}/extrait"

    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.get(url)
        response.raise_for_status()

    doc = lxml_html.document_fromstring(response.text)

    tab_parsers = {
        "fiche-info": ("tabpanel-fiche-info-panel", _parse_fiche_info),
        "rcp": ("tabpanel-rcp-panel", _parse_rcp),
        "notice": ("tabpanel-notice-panel", _parse_notice),
        "bon-usage": ("tabpanel-bon-usage-panel", _parse_bon_usage),
    }

    tabs: dict[str, dict] = {}
    toc: dict[str, list[dict]] = {}

    for tab_key, (panel_id, parser) in tab_parsers.items():
        panel = doc.get_element_by_id(panel_id, None)
        if panel is None:
            tabs[tab_key] = {}
            toc[tab_key] = []
            continue
        parsed = parser(panel)
        tabs[tab_key] = parsed
        toc[tab_key] = [
            {"id": sid, "titre": sec["titre"], "niveau": sec["niveau"]}
            for sid, sec in parsed.items()
        ]

    tool_context.state["med_doc"] = {"cis": cis, "tabs": tabs}
    tool_context.state["current_med_documentation"] = response.text

    return toc


async def read_section(
    tab: str, section_id: str, tool_context: ToolContext
) -> str:
    """Reads the text content of a section from the medication file.

    Args:
        tab: Target tab: 'rcp', 'notice', 'fiche-info' or 'bon-usage'.
        section_id: Section identifier (obtained via fetch_medication_doc).

    Returns:
        Formatted section content, or an error message.
    """
    med_doc = tool_context.state.get("med_doc")
    if med_doc is None:
        return "Error: call fetch_medication_doc first to download the medication file."

    tabs: dict[str, dict] = med_doc["tabs"]

    if tab not in tabs:
        return f"Unknown tab: '{tab}'. Available tabs: {list(tabs.keys())}"

    sections = tabs[tab]

    if section_id not in sections:
        return (
            f"Section '{section_id}' not found in tab '{tab}'. "
            f"Available sections: {list(sections.keys())}"
        )

    section = sections[section_id]
    return f"## {section['titre']}\n\n{section['contenu']}"
