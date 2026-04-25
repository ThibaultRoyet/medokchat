# med_documentation agent — Design Spec

**Date:** 2026-04-25  
**Status:** Approved

## Objectif

Créer un agent `med_documentation` qui, à partir d'un CIS (code identifiant de spécialité), télécharge la fiche officielle d'un médicament sur la Base de Données Publique des Médicaments (`base-donnees-publique.medicaments.gouv.fr`) et permet au LLM de naviguer dans son contenu pour répondre à des questions précises.

## Architecture

```
Orchestrator
  │
  ├─► med_finder(nom) ──────────────────────► state["med_informations"]["cis"]
  │
  └─► med_documentation(cis, question_user)
          │
          ├─ fetch_medication_doc(cis)   →  GET /medicament/{cis}/extrait
          │                                 parse HTML avec lxml
          │                                 stocke dans state["med_doc"]
          │                                 retourne ToC : {tab → [{id, titre, niveau}]}
          │
          └─ read_section(tab, section_id) → lit depuis state["med_doc"]
                                              retourne texte nettoyé
```

## Fichiers

```
agents/med_documentation/
  __init__.py
  agent.py      — Agent ADK (LiteLlm Claude) + instruction + 2 tools
  tools.py      — fetch_medication_doc + read_section
```

`agents/orchestrator.py` est mis à jour : import + `sub_agents` + instruction.

## Source de données

URL : `https://base-donnees-publique.medicaments.gouv.fr/medicament/{cis}/extrait`

La page est rendue côté serveur (pas de JS requis). Elle contient 4 onglets dans un seul document HTML :

| Tab ID | Contenu |
|--------|---------|
| `fiche-info` | Indications, composition, présentations, SMR/ASMR, autres infos |
| `rcp` | Résumé des Caractéristiques du Produit (sections 1–12) |
| `notice` | Notice patient avec sommaire latéral |
| `bon-usage` | Documents de bon usage (liens HAS, etc.) |

## Tools

### `fetch_medication_doc(cis: str, tool_context: ToolContext) → dict`

- GET sur l'URL officielle avec `httpx` (timeout 15s)
- Parse avec `lxml.html`
- Pour chaque onglet, extrait les sections à partir de :
  - RCP : éléments `<span id="...">` dans des `<p class="AmmAnnexeTitre1/2">`
  - Notice : liens du sommaire latéral (`fr-sidemenu__link`) + sections `<span id="...">`
  - Fiche-info : headings `<h5>` avec `id`
  - Bon-usage : contenu brut
- Stocke dans `state["med_doc"]` :
  ```json
  {
    "cis": "65089833",
    "tabs": {
      "rcp": {
        "4.3._Contre-indications": {
          "titre": "4.3. Contre-indications",
          "niveau": 2,
          "contenu": "texte nettoyé..."
        }
      },
      "notice": { ... },
      "fiche-info": { ... },
      "bon-usage": { ... }
    }
  }
  ```
- Retourne le ToC structuré (sans le contenu) pour que le LLM sache quoi demander

### `read_section(tab: str, section_id: str, tool_context: ToolContext) → str`

- Lit `state["med_doc"]["tabs"][tab][section_id]["contenu"]`
- Retourne le texte nettoyé (sans balises HTML, sans tooltips DSFR)
- Erreur explicite si `fetch_medication_doc` n'a pas été appelé (`med_doc` absent du state)
- Erreur explicite si `tab` ou `section_id` inconnu (avec liste des IDs valides)

## Agent

```python
Agent(
    model=LiteLlm("anthropic/{LLM_MODEL_NAME}"),
    name="med_documentation",
    description="Lit et navigue dans la fiche officielle d'un médicament (RCP, notice, bon usage) à partir de son CIS",
    instruction="""
    Tu reçois un CIS de médicament et une question.

    1. Appelle fetch_medication_doc(cis) pour obtenir la table des matières.
    2. Identifie les sections pertinentes selon la question.
    3. Appelle read_section(tab, section_id) pour chaque section utile.
    4. Synthétise une réponse claire et précise basée uniquement sur le contenu officiel.

    Si la question concerne la posologie, les contre-indications ou les effets indésirables,
    privilégie l'onglet "rcp". Pour les informations destinées au patient, utilise "notice".
    """,
    tools=[fetch_medication_doc, read_section],
)
```

## Intégration Orchestrateur

```python
from med_documentation.agent import root_agent as med_documentation_agent

root_agent = Agent(
    ...
    sub_agents=[med_finder_agent, med_documentation_agent],
    instruction="""
    - **med_finder** : recherche un médicament dans la base ANSM et retient son CIS
    - **med_documentation** : lit la fiche officielle (RCP, notice, bon usage) à partir du CIS.
      À appeler après med_finder quand l'utilisateur pose une question sur la posologie,
      les contre-indications, les effets indésirables, la notice patient, etc.
    """
)
```

## Flow exemple

1. User : *"Quelles sont les contre-indications du Doliprane ?"*
2. Orchestrateur → `med_finder("doliprane")` → CIS `65089833` dans state
3. Orchestrateur → `med_documentation` avec CIS + question
4. `fetch_medication_doc("65089833")` → ToC retourné au LLM
5. `read_section("rcp", "4.3._Contre-indications")` → texte des contre-indications
6. Réponse synthétisée à l'utilisateur

## Dépendances

Aucune nouvelle dépendance — `httpx` et `lxml` sont déjà présents dans le venv.
