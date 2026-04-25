# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**medokchat** is a monorepo for a multi-agent medical chat platform. The UI is a Next.js app using **CopilotKit + AG-UI**. The backend is a set of Python agents built on **Google ADK** and **LangGraph**, communicating via the **A2A protocol**.

## Commands

### Frontend

```bash
npm install          # Install JS dependencies
npm run dev          # Start everything (UI + all agents) concurrently
npm run dev:ui       # UI only — http://localhost:3000
npm run build
npm run lint
```

### Python agents (uv)

```bash
# First-time setup
cd agents && uv sync

# Run individual agents
npm run dev:orchestrator   # http://localhost:9000
npm run dev:research        # http://localhost:9001
npm run dev:analysis        # http://localhost:9002

# Or directly with uv
uv run --directory agents python orchestrator.py
```

### Environment

```bash
cp .env.example .env   # Then fill in GOOGLE_API_KEY and OPENAI_API_KEY
```

## Architecture

```
Browser (AG-UI client)
        │ AG-UI Protocol (HTTP/SSE)
        ▼
main.py :9000  (FastAPI + ADKAgent)
        │
        └──► orchestrator/agent.py  (Google ADK — root agent)
                │ ADK sub-agent delegation
                ├──► med_finder/agent.py
                │         └── tools.py  →  medicaments-api.giygas.dev (JSON)
                └──► med_documentation/agent.py
                          └── tools.py  →  base-donnees-publique.medicaments.gouv.fr (HTML)
```

## Agents

### orchestrator (`agents/orchestrator/`)

Point d'entrée de toutes les requêtes utilisateur. Reçoit la question, décide quel(s) sous-agent(s) appeler et dans quel ordre, puis synthétise la réponse finale.

**Stratégie de délégation :**
1. Toute mention d'un médicament → déléguer à `med_finder` pour identifier le CIS
2. Question détaillée (posologie, contre-indications, notice…) → déléguer à `med_documentation` avec le CIS

### med_finder (`agents/med_finder/`)

Recherche un médicament dans la base officielle ANSM via une API tierce et retient le médicament choisi en state.

**Tool :** `search_medicaments(name)` — appelle `medicaments-api.giygas.dev/v1/medicaments`

**State produit :** `state["med_informations"]` — dict complet du médicament (CIS, nom, forme, substances actives, statut)

**Pattern :** L'agent peut faire jusqu'à 5 recherches pour affiner. Un `after_model_callback` détecte le marqueur `CHOIX_CIS: <id>` dans la réponse du LLM et écrit le médicament choisi en state.

### med_documentation (`agents/med_documentation/`)

Lit la fiche officielle d'un médicament sur `base-donnees-publique.medicaments.gouv.fr` à partir de son CIS et navigue dans son contenu pour répondre à des questions précises.

**Tools :**

| Tool | Description |
|------|-------------|
| `fetch_medication_doc(cis)` | Télécharge `/medicament/{cis}/extrait`, parse les 4 onglets avec lxml, stocke tout dans `state["med_doc"]`, retourne la table des matières |
| `read_section(tab, section_id)` | Lit une section depuis le state — zéro réseau, retourne `## titre\n\ncontenu` |

**Onglets parsés :**

| Tab | Contenu |
|-----|---------|
| `fiche-info` | Indications, composition, présentations, SMR/ASMR |
| `rcp` | Résumé des Caractéristiques du Produit (sections 1–12, balisées `AmmAnnexeTitre1/2`) |
| `notice` | Notice patient — sommaire extrait des liens `fr-sidemenu__link` |
| `bon-usage` | Documents HAS/ANSM de bon usage |

**State produit :** `state["med_doc"] = {"cis": str, "tabs": {tab: {section_id: {"titre", "niveau", "contenu"}}}}`

### Ajouter un nouvel agent

1. Créer `agents/mon_agent/agent.py` et `__init__.py` en suivant le pattern `med_documentation/`
2. L'importer dans `agents/orchestrator/agent.py` et l'ajouter à `sub_agents`
3. Mettre à jour l'instruction de l'orchestrateur

## Key Files

| File | Role |
|------|------|
| `agents/main.py` | Point d'entrée — FastAPI + ADKAgent + uvicorn |
| `agents/orchestrator/agent.py` | Définition de l'agent orchestrateur |
| `agents/med_finder/agent.py` | Agent de recherche ANSM |
| `agents/med_documentation/agent.py` | Agent de lecture des fiches officielles |
| `agents/pyproject.toml` | Dépendances Python (uv) |
| `.env` | Clés API et ports |

## Environment Variables

| Variable | Used by |
|----------|---------|
| `LLM_MODEL_NAME` | Tous les agents (ex: `claude-sonnet-4-5`) |
| `ANTHROPIC_API_KEY` | Tous les agents (via LiteLlm) |
| `ORCHESTRATOR_PORT` | Port d'écoute de `main.py` (défaut: 9000) |
