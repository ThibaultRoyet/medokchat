# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**medokchat** est une plateforme multi-agent de chat médical construite sur **Google ADK**, avec une interface **Gradio**.

## Commands

```bash
# First-time setup
cd agents && uv sync

# Lancer l'interface Gradio (http://localhost:7860)
cd agents && uv run python ui.py

# Tests
cd agents && uv run pytest
```

### Environment

```bash
cp .env.example agents/.env   # Remplir ANTHROPIC_API_KEY et LLM_MODEL_NAME
```

## Architecture

```
Gradio UI (http://localhost:7860)
        │ ADK Runner (run_async)
        ▼
orchestrator/agent.py  (Google ADK — root agent)
        │ ADK sub-agent delegation
        ├──► med_finder/agent.py
        │         └── tools.py  →  medicaments-api.giygas.dev (JSON)
        └──► med_documentation/agent.py
                  └── tools.py  →  base-donnees-publique.medicaments.gouv.fr (HTML)
```

## Agents

### orchestrator (`agents/orchestrator/`)

Point d'entrée de toutes les requêtes utilisateur. Décide quel(s) sous-agent(s) appeler et dans quel ordre, puis synthétise la réponse finale.

**State lu :** `state["current_med"]` — médicament courant de la session (initialisé par `before_agent_callback`)

**Stratégie de délégation :**
1. Médicament déjà en `current_med` → utiliser son CIS directement, ne pas rappeler `med_finder`
2. Nouveau médicament mentionné → déléguer à `med_finder`
3. Question clinique (posologie, contre-indications, notice…) → déléguer à `med_documentation`

### med_finder (`agents/med_finder/`)

Identifie un médicament dans la base ANSM et transfère le contrôle à l'orchestrateur.

**Tools :**

| Tool | Description |
|------|-------------|
| `search_medicaments(name)` | Appelle `medicaments-api.giygas.dev/v1/medicaments`, stocke les résultats dans `state["_med_search_results"]` |
| `select_med(cis)` | Écrit le médicament choisi dans `state["med_informations"]` et `state["current_med"]`, puis `transfer_to_agent → orchestrator` |

**Pattern :** jusqu'à 5 appels `search_medicaments` pour affiner, puis obligatoirement `select_med`.

### med_documentation (`agents/med_documentation/`)

Lit la fiche officielle d'un médicament sur `base-donnees-publique.medicaments.gouv.fr` à partir de son CIS.

**Tools :**

| Tool | Description |
|------|-------------|
| `fetch_medication_doc(cis)` | Télécharge `/medicament/{cis}/extrait`, parse les 4 onglets avec lxml, stocke dans `state["med_doc"]`, retourne la table des matières |
| `read_section(tab, section_id)` | Lit une section depuis `state["med_doc"]` — zéro réseau, retourne `## titre\n\ncontenu` |

**Onglets parsés :**

| Tab | Contenu |
|-----|---------|
| `fiche-info` | Indications, composition, présentations, SMR/ASMR |
| `rcp` | Résumé des Caractéristiques du Produit (sections 1–12, balisées `AmmAnnexeTitre1/2`) |
| `notice` | Notice patient — sections extraites des liens `fr-sidemenu__link` |
| `bon-usage` | Documents HAS/ANSM de bon usage |

**State produit :** `state["med_doc"] = {"cis": str, "tabs": {tab: {section_id: {"titre", "niveau", "contenu"}}}}`

### ui (`agents/ui.py`)

Interface Gradio — point d'entrée principal.

**Layout :** deux colonnes — chat à gauche, iframe de la fiche officielle ANSM à droite.

**Pattern :** utilise `Runner` (ADK) en mode `run_async`. Chaque auteur ADK (`orchestrator`, `med_finder`, `med_documentation`) génère une bulle distincte avec titre et emoji. La fiche HTML est stockée dans `state["current_med_documentation"]` et affichée dans un `<iframe srcdoc>`.

### context_filter (`agents/context_filter.py`)

Callbacks `before_model_callback` partagés par tous les agents.

| Fonction | Rôle |
|----------|------|
| `keep_last_invocation` | Tronque l'historique à la dernière invocation utilisateur |
| `keep_orchestrator_context` | Dans les blocs `For context:` injectés par ADK, supprime les `function_call`/`function_response` des sous-agents et ne conserve que leurs réponses textuelles |

### Ajouter un nouvel agent

1. Créer `agents/mon_agent/agent.py` et `__init__.py` en suivant le pattern `med_documentation/`
2. L'importer dans `agents/orchestrator/agent.py` et l'ajouter à `sub_agents`
3. Mettre à jour l'instruction de l'orchestrateur

## Key Files

| File | Role |
|------|------|
| `agents/ui.py` | Point d'entrée — interface Gradio + ADK Runner |
| `agents/context_filter.py` | Callbacks de filtrage du contexte LLM |
| `agents/orchestrator/agent.py` | Agent orchestrateur |
| `agents/med_finder/agent.py` | Agent de recherche ANSM |
| `agents/med_documentation/agent.py` | Agent de lecture des fiches officielles |
| `agents/pyproject.toml` | Dépendances Python (uv) |
| `agents/.env` | Clés API (non versionné) |

## Environment Variables

| Variable | Used by |
|----------|---------|
| `LLM_MODEL_NAME` | Tous les agents (ex: `claude-sonnet-4-6`) |
| `ANTHROPIC_API_KEY` | Tous les agents (via LiteLlm) |
