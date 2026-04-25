import os
from google.adk import Agent
from google.adk.models import LiteLlm

from context_filter import keep_last_invocation
from .tools import fetch_medication_doc, read_section

root_agent = Agent(
    model=LiteLlm(
        model=f'anthropic/{os.getenv("LLM_MODEL_NAME")}',
        api_key=os.getenv("ANTHROPIC_API_KEY"),
    ),
    name="med_documentation",
    description="Lit et navigue dans la fiche officielle d'un médicament (RCP, notice, bon usage) à partir de son CIS",
    instruction="""
    Tu reçois une question sur un médicament.

    Médicament courant de la session :
    {current_med}

    Le CIS du médicament se trouve dans "Médicament courant" ci-dessus (ligne "CIS : ...").

    Procède toujours ainsi :
    1. Appelle fetch_medication_doc(cis) avec le CIS ci-dessus pour obtenir la table des matières.
    2. Identifie les sections pertinentes pour répondre à la question.
    3. Appelle read_section(tab, section_id) pour chaque section utile :
       - posologie, contre-indications, effets indésirables, interactions → onglet "rcp"
       - informations patient → onglet "notice"
       - indications, composition → onglet "fiche-info"
       - recommandations HAS/ANSM → onglet "bon-usage"
    4. Synthétise une réponse basée uniquement sur le contenu officiel récupéré.

    Si une section ne contient pas la réponse, explore d'autres sections avant de conclure.
    """,
    tools=[fetch_medication_doc, read_section],
    before_model_callback=keep_last_invocation,

)
