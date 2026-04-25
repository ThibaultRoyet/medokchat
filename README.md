# medokchat

Assistant médical multi-agent basé sur **Google ADK** et **Gradio**, spécialisé dans les informations sur les médicaments français (base ANSM).

## Fonctionnement

L'utilisateur pose une question sur un médicament. L'orchestrateur délègue :

1. **`med_finder`** — identifie le médicament dans la base ANSM et retourne son CIS
2. **`med_documentation`** — lit la fiche officielle (RCP, notice, bon usage) et répond à la question

## Lancement rapide

```bash
cd agents
cp ../.env.example .env      # remplir ANTHROPIC_API_KEY et LLM_MODEL_NAME
uv sync
uv run python ui.py          # http://localhost:7860
```

## Variables d'environnement

| Variable | Description |
|----------|-------------|
| `LLM_MODEL_NAME` | Modèle Claude (ex: `claude-sonnet-4-6`) |
| `ANTHROPIC_API_KEY` | Clé API Anthropic |

## Architecture

```
Gradio UI (http://localhost:7860)
        │ ADK Runner (run_async)
        ▼
orchestrator/agent.py
        ├──► med_finder/agent.py
        │         search_medicaments → medicaments-api.giygas.dev
        │         select_med → écrit state["current_med"]
        └──► med_documentation/agent.py
                  fetch_medication_doc → base-donnees-publique.medicaments.gouv.fr
                  read_section → lecture depuis state["med_doc"]
```

## Sources de données

- **Recherche médicament** : `medicaments-api.giygas.dev/v1/medicaments`
- **Fiche officielle** : `base-donnees-publique.medicaments.gouv.fr/medicament/{cis}/extrait`
