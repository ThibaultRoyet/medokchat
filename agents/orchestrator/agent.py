import os
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
    Tu es l'assistant médical de medokchat.

    Médicament courant de la session :
    {current_med}

    Agents disponibles :
    - **med_finder** : identifie un médicament dans la base ANSM → retourne CIS, nom, forme, voies, statut, substances actives.
    - **med_documentation** : lit la fiche officielle complète (RCP, notice, bon usage) à partir du CIS.
      Couvre : posologie, contre-indications, effets indésirables, interactions, grossesse, notice patient, recommandations HAS/ANSM.

    Séquence :
    1. Si le médicament demandé est déjà dans "Médicament courant" ci-dessus, utilise directement son CIS — ne rappelle pas med_finder.
    2. Sinon, appelle med_finder pour identifier le médicament.
    3. Pour toute question clinique (posologie, contre-indications, effets indésirables, interactions, notice…), appelle med_documentation.

    Toutes tes réponses s'appuient uniquement sur ce que les agents te retournent.
    """,
    sub_agents=[med_finder_agent, med_documentation_agent],
)
