# med_documentation Agent — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Créer l'agent `med_documentation` qui télécharge et navigue dans la fiche officielle d'un médicament (base-donnees-publique.medicaments.gouv.fr) via son CIS pour répondre aux questions de l'utilisateur.

**Architecture:** L'agent expose deux tools : `fetch_medication_doc` (télécharge la page HTML, parse les 4 onglets, stocke dans state, retourne le ToC) et `read_section` (lit une section depuis le state). L'orchestrateur le délègue après `med_finder`.

**Tech Stack:** Python, Google ADK, LiteLlm (Claude), httpx, lxml, pytest, respx

---

## File Map

| Fichier | Action | Rôle |
|---------|--------|------|
| `agents/med_documentation/__init__.py` | Créer | Export `root_agent` |
| `agents/med_documentation/tools.py` | Créer | `fetch_medication_doc` + `read_section` |
| `agents/med_documentation/agent.py` | Créer | Définition de l'agent ADK |
| `agents/tests/__init__.py` | Créer | Package de tests |
| `agents/tests/test_med_documentation_tools.py` | Créer | Tests des deux tools |
| `agents/tests/fixtures/med_page.html` | Créer | HTML minimal pour les tests |
| `agents/pyproject.toml` | Modifier | Ajouter `pytest`, `pytest-asyncio`, `respx` en dev deps |
| `agents/orchestrator.py` | Modifier | Ajouter `med_documentation` en sub_agent |

---

## Task 1 : Dev dependencies + scaffold de tests

**Files:**
- Modify: `agents/pyproject.toml`
- Create: `agents/tests/__init__.py`

- [ ] **Ajouter les deps de test dans `pyproject.toml`**

Remplacer :
```toml
[tool.uv]
dev-dependencies = []
```
Par :
```toml
[tool.uv]
dev-dependencies = [
    "pytest>=8.0.0",
    "pytest-asyncio>=0.24.0",
    "respx>=0.21.0",
]

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
```

- [ ] **Installer les deps**

```bash
cd agents && uv sync
```

Expected : résolution sans erreur, `pytest` disponible dans le venv.

- [ ] **Créer `agents/tests/__init__.py`**

```python
```
(fichier vide)

- [ ] **Vérifier que pytest tourne**

```bash
cd agents && uv run pytest --collect-only
```

Expected : `no tests ran` sans erreur.

- [ ] **Commit**

```bash
git add agents/pyproject.toml agents/uv.lock agents/tests/__init__.py
git commit -m "chore: add pytest/respx dev deps for med_documentation tests"
```

---

## Task 2 : Fixture HTML pour les tests

**Files:**
- Create: `agents/tests/fixtures/med_page.html`

Cette fixture reproduit la structure minimale de la vraie page pour tester le parsing sans appel réseau.

- [ ] **Créer le répertoire et la fixture**

```bash
mkdir -p agents/tests/fixtures
```

Créer `agents/tests/fixtures/med_page.html` :

```html
<!DOCTYPE html>
<html lang="fr">
<head><meta charset="UTF-8"><title>Test médicament</title></head>
<body>
<div id="tabpanel-fiche-info-panel" class="fr-tabs__panel fr-tabs__panel--selected" role="tabpanel">
  <section>
    <h5 id="heading-indications-therapeutiques">Indications thérapeutiques</h5>
    <p>Traitement symptomatique des douleurs légères à modérées.</p>
    <h5 id="heading-composition-substances-active">Composition en substances actives</h5>
    <p>Paracétamol 1000 mg</p>
  </section>
</div>

<div id="tabpanel-rcp-panel" class="fr-tabs__panel" role="tabpanel">
  <div id="contenu" class="fr-col-12 fr-col-md-8">
    <p class="AmmAnnexeTitre1"><a name="RcpDenomination"><span id="1._DENOMINATION_DU_MEDICAMENT">1. DENOMINATION DU MEDICAMENT</span></a></p>
    <p>DOLIPRANE 1000 mg, comprimé</p>
    <p class="AmmAnnexeTitre2"><a name="RcpIndicTherap"><span id="4.1._Indications_thérapeutiques">4.1. Indications thérapeutiques</span></a></p>
    <p>Traitement symptomatique des douleurs légères à modérées et/ou de la fièvre.</p>
    <p class="AmmAnnexeTitre2"><a name="RcpContreindications"><span id="4.3._Contre-indications">4.3. Contre-indications</span></a></p>
    <p>Hypersensibilité au paracétamol ou à l'un des excipients.</p>
    <p>Insuffisance hépatocellulaire sévère.</p>
    <p class="AmmAnnexeTitre1"><a name="RcpTitulaireAmm"><span id="7._TITULAIRE_DE_L'AUTORISATION_DE_MISE_SUR_LE_MARCHE">7. TITULAIRE DE L'AUTORISATION DE MISE SUR LE MARCHE</span></a></p>
    <p>OPELLA HEALTHCARE FRANCE SAS</p>
  </div>
</div>

<div id="tabpanel-notice-panel" class="fr-tabs__panel" role="tabpanel">
  <div class="fr-sidemenu">
    <nav>
      <a class="fr-sidemenu__link" href="#Que_contient_cette_notice_?">Que contient cette notice ?</a>
      <a class="fr-sidemenu__link" href="#1._Qu_est-ce_que_DOLIPRANE_et_dans_quels_cas_est-il_utilisé_?">1. Qu'est-ce que DOLIPRANE</a>
      <a class="fr-sidemenu__link" href="#4._Quels_sont_les_effets_indésirables_éventuels_?">4. Effets indésirables</a>
    </nav>
  </div>
  <div id="notice-content">
    <p><a name="Ann3bSomm"><span id="Que_contient_cette_notice_?">Que contient cette notice ?</span></a></p>
    <p>1. Qu'est-ce que DOLIPRANE et dans quels cas est-il utilisé ?</p>
    <p>2. Quelles sont les informations à connaître avant de prendre DOLIPRANE ?</p>
    <p><a name="Ann3b1"><span id="1._Qu_est-ce_que_DOLIPRANE_et_dans_quels_cas_est-il_utilisé_?">1. Qu'est-ce que DOLIPRANE et dans quels cas est-il utilisé ?</span></a></p>
    <p>DOLIPRANE est un antalgique et antipyrétique.</p>
    <p>Il est utilisé pour traiter les douleurs et la fièvre.</p>
    <p><a name="Ann3b4"><span id="4._Quels_sont_les_effets_indésirables_éventuels_?">4. Quels sont les effets indésirables éventuels ?</span></a></p>
    <p>Rares : réactions allergiques.</p>
  </div>
</div>

<div id="tabpanel-bon-usage-panel" class="fr-tabs__panel" role="tabpanel">
  <ul>
    <li><a href="https://www.has-sante.fr/jcms/c_2674284/" target="_blank">Prise en charge de la fièvre chez l'enfant</a></li>
  </ul>
</div>
</body>
</html>
```

- [ ] **Commit**

```bash
git add agents/tests/fixtures/med_page.html
git commit -m "test: add HTML fixture for med_documentation parsing tests"
```

---

## Task 3 : Implémenter et tester `fetch_medication_doc`

**Files:**
- Create: `agents/med_documentation/tools.py`
- Create: `agents/tests/test_med_documentation_tools.py`

- [ ] **Écrire le test qui va échouer**

Créer `agents/tests/test_med_documentation_tools.py` :

```python
import pytest
import respx
import httpx
from pathlib import Path
from unittest.mock import MagicMock

FIXTURE_HTML = (Path(__file__).parent / "fixtures" / "med_page.html").read_text()
BASE_URL = "https://base-donnees-publique.medicaments.gouv.fr/medicament/{cis}/extrait"


def make_tool_context(initial_state: dict | None = None) -> MagicMock:
    ctx = MagicMock()
    ctx.state = initial_state or {}
    return ctx


@respx.mock
async def test_fetch_stores_rcp_sections_in_state():
    cis = "65089833"
    respx.get(BASE_URL.format(cis=cis)).mock(
        return_value=httpx.Response(200, text=FIXTURE_HTML)
    )
    ctx = make_tool_context()

    from med_documentation.tools import fetch_medication_doc
    toc = await fetch_medication_doc(cis, ctx)

    assert "med_doc" in ctx.state
    assert "rcp" in ctx.state["med_doc"]["tabs"]
    rcp = ctx.state["med_doc"]["tabs"]["rcp"]
    assert "4.3._Contre-indications" in rcp
    assert "Hypersensibilité" in rcp["4.3._Contre-indications"]["contenu"]


@respx.mock
async def test_fetch_returns_toc_structure():
    cis = "65089833"
    respx.get(BASE_URL.format(cis=cis)).mock(
        return_value=httpx.Response(200, text=FIXTURE_HTML)
    )
    ctx = make_tool_context()

    from med_documentation.tools import fetch_medication_doc
    toc = await fetch_medication_doc(cis, ctx)

    assert "rcp" in toc
    assert isinstance(toc["rcp"], list)
    ids = [s["id"] for s in toc["rcp"]]
    assert "4.3._Contre-indications" in ids
    assert "1._DENOMINATION_DU_MEDICAMENT" in ids


@respx.mock
async def test_fetch_stores_notice_sections_in_state():
    cis = "65089833"
    respx.get(BASE_URL.format(cis=cis)).mock(
        return_value=httpx.Response(200, text=FIXTURE_HTML)
    )
    ctx = make_tool_context()

    from med_documentation.tools import fetch_medication_doc
    await fetch_medication_doc(cis, ctx)

    notice = ctx.state["med_doc"]["tabs"]["notice"]
    assert "Que_contient_cette_notice_?" in notice
    toc_section = notice["Que_contient_cette_notice_?"]
    assert toc_section["titre"] == "Que contient cette notice ?"
```

- [ ] **Vérifier que les tests échouent**

```bash
cd agents && uv run pytest tests/test_med_documentation_tools.py::test_fetch_stores_rcp_sections_in_state -v
```

Expected : `ModuleNotFoundError: No module named 'med_documentation'`

- [ ] **Créer `agents/med_documentation/__init__.py`**

```python
from .agent import root_agent
```

(on peut temporairement commenter l'import le temps d'implémenter `tools.py` d'abord — voir étape suivante)

En attendant `agent.py`, créer un `__init__.py` vide :
```python
```

- [ ] **Implémenter `agents/med_documentation/tools.py`**

```python
import re
import httpx
from lxml import html as lxml_html
from google.adk.tools.tool_context import ToolContext

_BASE_URL = "https://base-donnees-publique.medicaments.gouv.fr/medicament/{cis}/extrait"

_TAB_PANEL_IDS = {
    "fiche-info": "tabpanel-fiche-info-panel",
    "rcp": "tabpanel-rcp-panel",
    "notice": "tabpanel-notice-panel",
    "bon-usage": "tabpanel-bon-usage-panel",
}


def _clean(element) -> str:
    return re.sub(r"\s+", " ", element.text_content()).strip()


def _parse_rcp(panel) -> dict[str, dict]:
    """Parse RCP sections via AmmAnnexeTitre1/2 CSS class markers."""
    sections: dict[str, dict] = {}
    content_div = panel.find('.//*[@id="contenu"]')
    if content_div is None:
        return sections

    current_id: str | None = None
    current_titre = ""
    current_level = 1
    current_texts: list[str] = []

    for child in list(content_div):
        cls = child.get("class") or ""
        is_h1 = "AmmAnnexeTitre1" in cls
        is_h2 = "AmmAnnexeTitre2" in cls

        if is_h1 or is_h2:
            if current_id:
                sections[current_id] = {
                    "titre": current_titre,
                    "niveau": current_level,
                    "contenu": "\n".join(current_texts).strip(),
                }
            span = child.find('.//*[@id]')
            if span is not None and span.get("id"):
                current_id = span.get("id")
                current_titre = _clean(span)
                current_level = 1 if is_h1 else 2
                current_texts = []
            else:
                current_id = None
        elif current_id:
            text = _clean(child)
            if text:
                current_texts.append(text)

    if current_id:
        sections[current_id] = {
            "titre": current_titre,
            "niveau": current_level,
            "contenu": "\n".join(current_texts).strip(),
        }

    return sections


def _parse_notice(panel) -> dict[str, dict]:
    """Parse notice sections from sidebar ToC + matching span IDs."""
    sections: dict[str, dict] = {}

    # Collect ordered section IDs from sidebar
    sidebar_ids: dict[str, str] = {}
    for link in panel.xpath('.//*[contains(@class, "fr-sidemenu__link")]'):
        href = (link.get("href") or "").strip()
        if href.startswith("#"):
            section_id = href[1:]
            sidebar_ids[section_id] = _clean(link)

    if not sidebar_ids:
        return sections

    # For each section, find its span and collect following sibling text
    for section_id, titre in sidebar_ids.items():
        span = panel.find(f'.//*[@id="{section_id}"]')
        if span is None:
            continue
        # Walk up to find a container whose children we can iterate
        anchor = span.getparent()  # <a name="...">
        if anchor is None:
            continue
        heading_p = anchor.getparent()  # <p> holding the anchor
        if heading_p is None:
            continue
        content_div = heading_p.getparent()
        if content_div is None:
            continue

        collecting = False
        texts: list[str] = []
        for elem in list(content_div):
            if elem is heading_p:
                collecting = True
                continue
            if not collecting:
                continue
            # Stop at the next known section heading
            inner_span = elem.find('.//*[@id]')
            if inner_span is not None and inner_span.get("id") in sidebar_ids:
                break
            text = _clean(elem)
            if text:
                texts.append(text)

        sections[section_id] = {
            "titre": titre,
            "niveau": 1,
            "contenu": "\n".join(texts).strip(),
        }

    return sections


def _parse_fiche_info(panel) -> dict[str, dict]:
    """Parse fiche-info sections via h5[id] headings."""
    sections: dict[str, dict] = {}
    headings = panel.xpath('.//h5[@id]')

    for i, h5 in enumerate(headings):
        section_id = h5.get("id")
        titre = _clean(h5)
        # Collect sibling text until the next h5
        # Walk parent's children between this h5 and next
        parent = h5.getparent()
        if parent is None:
            continue
        children = list(parent)
        try:
            start = children.index(h5)
        except ValueError:
            continue
        end = children.index(headings[i + 1]) if i + 1 < len(headings) else len(children)

        texts = [_clean(c) for c in children[start + 1:end] if _clean(c)]
        sections[section_id] = {
            "titre": titre,
            "niveau": 1,
            "contenu": "\n".join(texts).strip(),
        }

    return sections


def _parse_bon_usage(panel) -> dict[str, dict]:
    """Extract bon-usage as a single flat section."""
    text = _clean(panel)
    if not text:
        return {}
    return {
        "bon-usage": {
            "titre": "Documents de bon usage",
            "niveau": 1,
            "contenu": text,
        }
    }


def _build_toc(tabs: dict[str, dict[str, dict]]) -> dict[str, list[dict]]:
    return {
        tab: [
            {"id": sid, "titre": s["titre"], "niveau": s["niveau"]}
            for sid, s in sections.items()
        ]
        for tab, sections in tabs.items()
    }


async def fetch_medication_doc(cis: str, tool_context: ToolContext) -> dict:
    """Télécharge la fiche officielle d'un médicament et retourne la table des matières.

    Args:
        cis: Code Identifiant de Spécialité du médicament.

    Returns:
        Table des matières structurée par onglet :
        {"rcp": [{"id": ..., "titre": ..., "niveau": ...}], "notice": [...], ...}
    """
    url = _BASE_URL.format(cis=cis)
    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.get(url)
        response.raise_for_status()

    tree = lxml_html.document_fromstring(response.text)

    parsers = {
        "fiche-info": _parse_fiche_info,
        "rcp": _parse_rcp,
        "notice": _parse_notice,
        "bon-usage": _parse_bon_usage,
    }

    tabs: dict[str, dict[str, dict]] = {}
    for tab_name, panel_id in _TAB_PANEL_IDS.items():
        panel = tree.get_element_by_id(panel_id, None)
        if panel is not None:
            tabs[tab_name] = parsers[tab_name](panel)
        else:
            tabs[tab_name] = {}

    tool_context.state["med_doc"] = {"cis": cis, "tabs": tabs}
    return _build_toc(tabs)


async def read_section(tab: str, section_id: str, tool_context: ToolContext) -> str:
    """Lit le contenu d'une section depuis la fiche médicament déjà téléchargée.

    Args:
        tab: Onglet cible — "fiche-info", "rcp", "notice" ou "bon-usage".
        section_id: Identifiant de la section tel qu'il apparaît dans la table des matières.

    Returns:
        Texte de la section.
    """
    med_doc = tool_context.state.get("med_doc")
    if med_doc is None:
        return "Erreur : appelez d'abord fetch_medication_doc pour télécharger la fiche."

    tabs = med_doc.get("tabs", {})
    valid_tabs = list(tabs.keys())
    if tab not in tabs:
        return f"Onglet inconnu : '{tab}'. Onglets disponibles : {valid_tabs}"

    sections = tabs[tab]
    if section_id not in sections:
        valid_ids = list(sections.keys())
        return (
            f"Section '{section_id}' introuvable dans l'onglet '{tab}'. "
            f"Sections disponibles : {valid_ids}"
        )

    section = sections[section_id]
    return f"## {section['titre']}\n\n{section['contenu']}"
```

- [ ] **Lancer les tests**

```bash
cd agents && uv run pytest tests/test_med_documentation_tools.py -v
```

Expected : les 3 tests passent en vert.

- [ ] **Commit**

```bash
git add agents/med_documentation/tools.py agents/med_documentation/__init__.py agents/tests/test_med_documentation_tools.py
git commit -m "feat: add med_documentation tools (fetch + read_section)"
```

---

## Task 4 : Tester `read_section`

**Files:**
- Modify: `agents/tests/test_med_documentation_tools.py`

- [ ] **Ajouter les tests de `read_section` dans le fichier de tests existant**

Ajouter à la fin de `agents/tests/test_med_documentation_tools.py` :

```python
async def test_read_section_returns_content():
    ctx = make_tool_context({
        "med_doc": {
            "cis": "65089833",
            "tabs": {
                "rcp": {
                    "4.3._Contre-indications": {
                        "titre": "4.3. Contre-indications",
                        "niveau": 2,
                        "contenu": "Hypersensibilité au paracétamol.",
                    }
                }
            },
        }
    })

    from med_documentation.tools import read_section
    result = await read_section("rcp", "4.3._Contre-indications", ctx)

    assert "4.3. Contre-indications" in result
    assert "Hypersensibilité" in result


async def test_read_section_error_no_doc():
    ctx = make_tool_context()

    from med_documentation.tools import read_section
    result = await read_section("rcp", "4.3._Contre-indications", ctx)

    assert "fetch_medication_doc" in result


async def test_read_section_error_unknown_tab():
    ctx = make_tool_context({
        "med_doc": {"cis": "123", "tabs": {"rcp": {}}}
    })

    from med_documentation.tools import read_section
    result = await read_section("inexistant", "4.3._Contre-indications", ctx)

    assert "inexistant" in result
    assert "rcp" in result


async def test_read_section_error_unknown_section():
    ctx = make_tool_context({
        "med_doc": {
            "cis": "123",
            "tabs": {"rcp": {"4.3._Contre-indications": {"titre": "CI", "niveau": 2, "contenu": "..."}}}
        }
    })

    from med_documentation.tools import read_section
    result = await read_section("rcp", "section-inconnue", ctx)

    assert "section-inconnue" in result
    assert "4.3._Contre-indications" in result
```

- [ ] **Lancer tous les tests**

```bash
cd agents && uv run pytest tests/test_med_documentation_tools.py -v
```

Expected : 7 tests passent.

- [ ] **Commit**

```bash
git add agents/tests/test_med_documentation_tools.py
git commit -m "test: add read_section unit tests"
```

---

## Task 5 : Créer `agent.py`

**Files:**
- Create: `agents/med_documentation/agent.py`
- Modify: `agents/med_documentation/__init__.py`

- [ ] **Créer `agents/med_documentation/agent.py`**

```python
import os
from google.adk import Agent
from google.adk.models import LiteLlm

from .tools import fetch_medication_doc, read_section

root_agent = Agent(
    model=LiteLlm(
        model=f'anthropic/{os.getenv("LLM_MODEL_NAME")}',
        api_key=os.getenv("ANTHROPIC_API_KEY"),
    ),
    name="med_documentation",
    description="Lit et navigue dans la fiche officielle d'un médicament (RCP, notice, bon usage) à partir de son CIS",
    instruction="""
    Tu reçois un CIS de médicament et une question de l'utilisateur.

    Procède toujours ainsi :
    1. Appelle fetch_medication_doc(cis) pour télécharger la fiche et obtenir la table des matières.
    2. Identifie les sections pertinentes pour répondre à la question.
    3. Appelle read_section(tab, section_id) pour chaque section utile.
       - Pour la posologie, les contre-indications, les effets indésirables : utilise l'onglet "rcp"
       - Pour les informations destinées au patient (notice) : utilise l'onglet "notice"
       - Pour les informations générales (indications, composition) : utilise l'onglet "fiche-info"
    4. Synthétise une réponse claire et précise basée uniquement sur le contenu officiel.

    Ne fabrique pas d'informations. Si une section ne contient pas la réponse, consultes-en une autre.
    """,
    tools=[fetch_medication_doc, read_section],
)
```

- [ ] **Mettre à jour `agents/med_documentation/__init__.py`**

```python
from .agent import root_agent
```

- [ ] **Vérifier que l'import fonctionne**

```bash
cd agents && uv run python -c "from med_documentation import root_agent; print(root_agent.name)"
```

Expected : `med_documentation`

- [ ] **Commit**

```bash
git add agents/med_documentation/agent.py agents/med_documentation/__init__.py
git commit -m "feat: add med_documentation agent definition"
```

---

## Task 6 : Mettre à jour l'orchestrateur

**Files:**
- Modify: `agents/orchestrator.py`

- [ ] **Modifier `agents/orchestrator.py`**

Remplacer le contenu par :

```python
from __future__ import annotations

from dotenv import load_dotenv
load_dotenv()

import os
import uvicorn
from fastapi import FastAPI
from ag_ui_adk import ADKAgent, add_adk_fastapi_endpoint
from google.adk import Agent
from google.adk.models import LiteLlm

from med_finder.agent import root_agent as med_finder_agent
from med_documentation.agent import root_agent as med_documentation_agent

root_agent = Agent(
    model=LiteLlm(
        model=f'anthropic/{os.getenv("LLM_MODEL_NAME")}',
        api_key=os.getenv("ANTHROPIC_API_KEY"),
    ),
    name="orchestrator",
    description="Orchestrateur principal de medokchat",
    instruction="""
    Tu es l'assistant médical principal de medokchat.
    Tu aides les utilisateurs à trouver des informations sur les médicaments.

    Tu as accès aux agents spécialisés suivants :
    - **med_finder** : recherche un médicament dans la base officielle française (ANSM)
      et retient les informations de base du médicament choisi (CIS inclus).
    - **med_documentation** : lit la fiche officielle d'un médicament (RCP, notice, bon usage)
      à partir de son CIS. Fournit des informations détaillées sur la posologie, les
      contre-indications, les effets indésirables, la notice patient, etc.

    Stratégie de délégation :
    1. Quand l'utilisateur mentionne un médicament, commence par déléguer à **med_finder**
       pour identifier le médicament et obtenir son CIS.
    2. Si l'utilisateur pose une question détaillée (posologie, contre-indications,
       effets indésirables, notice, interactions, grossesse…), délègue ensuite à
       **med_documentation** en lui transmettant le CIS et la question.
    """,
    sub_agents=[med_finder_agent, med_documentation_agent],
)

adk_orchestrator_agent = ADKAgent(
    adk_agent=root_agent,
    app_name="orchestrator_app",
    user_id="demo_user",
    session_timeout_seconds=3600,
    use_in_memory_services=True,
)

app = FastAPI(title="medokchat — Orchestrateur (ADK + AG-UI)")
add_adk_fastapi_endpoint(app, adk_orchestrator_agent, path="/")

if __name__ == "__main__":
    port = int(os.getenv("ORCHESTRATOR_PORT", 9000))
    print(f"Starting orchestrator on http://localhost:{port}")
    uvicorn.run(app, host="0.0.0.0", port=port)
```

- [ ] **Vérifier que l'import de l'orchestrateur fonctionne**

```bash
cd agents && uv run python -c "from orchestrator import root_agent; print([a.name for a in root_agent.sub_agents])"
```

Expected : `['med_finder', 'med_documentation']`

- [ ] **Lancer la suite de tests complète**

```bash
cd agents && uv run pytest tests/ -v
```

Expected : tous les tests passent.

- [ ] **Commit**

```bash
git add agents/orchestrator.py
git commit -m "feat: wire med_documentation into orchestrator"
```

---

## Task 7 : Test d'intégration manuel

- [ ] **Démarrer l'orchestrateur**

```bash
cd agents && uv run python orchestrator.py
```

Expected : `Starting orchestrator on http://localhost:9000`

- [ ] **Tester le flow complet via curl**

Dans un autre terminal :

```bash
curl -X POST http://localhost:9000/ \
  -H "Content-Type: application/json" \
  -d '{"messages": [{"role": "user", "content": "Quelles sont les contre-indications du Doliprane 1000mg ?"}]}'
```

Expected :
1. L'orchestrateur délègue à `med_finder` → trouve le CIS
2. L'orchestrateur délègue à `med_documentation` → lit la section `4.3._Contre-indications` du RCP
3. La réponse cite les contre-indications officielles (hypersensibilité au paracétamol, insuffisance hépatocellulaire)

- [ ] **Tester la navigation dans la notice**

```bash
curl -X POST http://localhost:9000/ \
  -H "Content-Type: application/json" \
  -d '{"messages": [{"role": "user", "content": "Que contient la notice du Doliprane 1000mg ?"}]}'
```

Expected : l'agent consulte l'onglet `notice`, section `Que_contient_cette_notice_?`, et retourne les rubriques de la notice.
