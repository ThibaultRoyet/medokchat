"""Tests des parsers et tools de med_documentation.

Utilise le vrai HTML téléchargé dans med_doc.html (DOLIPRANE 1000 mg, CIS 65089833).
"""
from pathlib import Path
from unittest.mock import MagicMock

import pytest
import respx
import httpx
from lxml import html as lxml_html

from med_documentation.tools import (
    _parse_fiche_info,
    _parse_notice,
    _parse_rcp,
    fetch_medication_doc,
    read_section,
)

FIXTURE_HTML = Path(__file__).parent.parent / "med_doc.html"


@pytest.fixture(scope="module")
def doc():
    return lxml_html.document_fromstring(FIXTURE_HTML.read_text())


@pytest.fixture(scope="module")
def rcp_sections(doc):
    return _parse_rcp(doc.get_element_by_id("tabpanel-rcp-panel"))


@pytest.fixture(scope="module")
def notice_sections(doc):
    return _parse_notice(doc.get_element_by_id("tabpanel-notice-panel"))


@pytest.fixture(scope="module")
def fiche_sections(doc):
    return _parse_fiche_info(doc.get_element_by_id("tabpanel-fiche-info-panel"))


def make_ctx(state=None):
    ctx = MagicMock()
    ctx.state = state or {}
    return ctx


# ---------------------------------------------------------------------------
# _parse_rcp
# ---------------------------------------------------------------------------


def test_rcp_no_crash_on_html_comments(rcp_sections):
    """Le bug d'origine : HtmlComment levait ValueError dans text_content()."""
    assert isinstance(rcp_sections, dict)
    assert len(rcp_sections) > 0


def test_rcp_finds_expected_sections(rcp_sections):
    assert "1._DENOMINATION_DU_MEDICAMENT" in rcp_sections
    assert "4.3._Contre-indications" in rcp_sections
    assert "4.2._Posologie_et_mode_d_administration" in rcp_sections


def test_rcp_section_has_required_keys(rcp_sections):
    section = rcp_sections["4.3._Contre-indications"]
    assert "titre" in section
    assert "niveau" in section
    assert "contenu" in section


def test_rcp_contre_indications_content(rcp_sections):
    contenu = rcp_sections["4.3._Contre-indications"]["contenu"]
    assert "Hypersensibilité" in contenu
    assert "paracétamol" in contenu


def test_rcp_posologie_content(rcp_sections):
    contenu = rcp_sections["4.2._Posologie_et_mode_d_administration"]["contenu"]
    assert "1000 mg" in contenu or "paracétamol" in contenu


def test_rcp_niveau_h1_vs_h2(rcp_sections):
    assert rcp_sections["1._DENOMINATION_DU_MEDICAMENT"]["niveau"] == 1
    assert rcp_sections["4.3._Contre-indications"]["niveau"] == 2


# ---------------------------------------------------------------------------
# _parse_notice
# ---------------------------------------------------------------------------


def test_notice_finds_sommaire_sections(notice_sections):
    assert "Que_contient_cette_notice_?" in notice_sections
    assert "Dénomination_du_médicament" in notice_sections


def test_notice_denomination_content(notice_sections):
    contenu = notice_sections["Dénomination_du_médicament"]["contenu"]
    assert "DOLIPRANE" in contenu
    assert "paracétamol" in contenu.lower() or "Paracétamol" in contenu


def test_notice_section_has_required_keys(notice_sections):
    section = notice_sections["Dénomination_du_médicament"]
    assert "titre" in section
    assert "niveau" in section
    assert "contenu" in section


# ---------------------------------------------------------------------------
# _parse_fiche_info
# ---------------------------------------------------------------------------


def test_fiche_finds_headings(fiche_sections):
    assert "heading-indications-therapeutiques" in fiche_sections
    assert "heading-composition-substances-active" in fiche_sections


def test_fiche_indications_content(fiche_sections):
    contenu = fiche_sections["heading-indications-therapeutiques"]["contenu"]
    assert "paracétamol" in contenu.lower() or "DOLIPRANE" in contenu


# ---------------------------------------------------------------------------
# read_section
# ---------------------------------------------------------------------------


async def test_read_section_returns_formatted_content():
    ctx = make_ctx({
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
    result = await read_section("rcp", "4.3._Contre-indications", ctx)
    assert result == "## 4.3. Contre-indications\n\nHypersensibilité au paracétamol."


async def test_read_section_error_no_doc():
    ctx = make_ctx()
    result = await read_section("rcp", "anything", ctx)
    assert "fetch_medication_doc" in result


async def test_read_section_error_unknown_tab():
    ctx = make_ctx({"med_doc": {"cis": "x", "tabs": {"rcp": {}}}})
    result = await read_section("inexistant", "x", ctx)
    assert "inexistant" in result
    assert "rcp" in result


async def test_read_section_error_unknown_section():
    ctx = make_ctx({
        "med_doc": {
            "cis": "x",
            "tabs": {"rcp": {"4.3._Contre-indications": {"titre": "CI", "niveau": 2, "contenu": "..."}}},
        }
    })
    result = await read_section("rcp", "section-inconnue", ctx)
    assert "section-inconnue" in result
    assert "4.3._Contre-indications" in result


# ---------------------------------------------------------------------------
# fetch_medication_doc (intégration légère avec mock réseau)
# ---------------------------------------------------------------------------


@respx.mock
async def test_fetch_stores_in_state_and_returns_toc():
    cis = "65089833"
    html_content = FIXTURE_HTML.read_text()
    respx.get(f"https://base-donnees-publique.medicaments.gouv.fr/medicament/{cis}/extrait").mock(
        return_value=httpx.Response(200, text=html_content)
    )
    ctx = make_ctx()

    toc = await fetch_medication_doc(cis, ctx)

    assert "med_doc" in ctx.state
    assert ctx.state["med_doc"]["cis"] == cis
    assert "rcp" in ctx.state["med_doc"]["tabs"]
    assert "4.3._Contre-indications" in ctx.state["med_doc"]["tabs"]["rcp"]

    assert "rcp" in toc
    toc_ids = [s["id"] for s in toc["rcp"]]
    assert "4.3._Contre-indications" in toc_ids
    first = toc["rcp"][0]
    assert set(first.keys()) == {"id", "titre", "niveau"}
