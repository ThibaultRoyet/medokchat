import os

from google.adk import Agent
from google.adk.models import LiteLlm

from context_filter import keep_orchestrator_context
from .tools import search_medicaments, select_med


root_agent = Agent(
    model=LiteLlm(
        model=f'anthropic/{os.getenv("LLM_MODEL_NAME")}',
        api_key=os.getenv("ANTHROPIC_API_KEY"),
    ),
    name="med_finder",
    description="Identifie un médicament dans la base officielle française (ANSM) et retourne son CIS",
    instruction="""
    Ton unique objectif : identifier le médicament dans la base ANSM et appeler select_med avec son CIS.

    Procédure :
    1. Appelle search_medicaments avec le nom du médicament (nom seul, sans dosage ni forme).
       Jusqu'à 5 tentatives — commence spécifique, élargis si aucun résultat.
    2. Sélectionne le résultat le plus pertinent :
       - Correspondance maximale avec la demande
       - Statut "Commercialisée" préférable
       - Forme pharmaceutique adaptée si précisée
    3. Appelle select_med(cis) avec le CIS du médicament choisi.

    RÈGLE ABSOLUE : tu dois toujours terminer par un appel à select_med.
    Si aucun médicament n'est trouvé après 5 tentatives, arrête-toi sans appeler select_med.
    """,
    tools=[search_medicaments, select_med],
    before_model_callback=keep_orchestrator_context,
)
