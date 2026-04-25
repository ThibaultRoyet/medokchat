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
