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
