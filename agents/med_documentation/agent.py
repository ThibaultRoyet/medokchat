import os
from google.adk import Agent
from google.adk.models import LiteLlm

from .tools import fetch_medication_doc, read_section

root_agent = Agent(
    model=LiteLlm(
        model=f'anthropic/{os.getenv("LLM_MODEL_NAME")}',
        api_key=os.getenv("ANTHROPIC_API_KEY"),
    ),
    name="med_documentation",
    description="Lit et navigue dans la fiche officielle d'un médicament (RCP, notice, bon usage) à partir de son CIS",
    instruction="""
    Tu reçois un CIS de médicament et une question de l'utilisateur.
    Le CIS te sera transmis explicitement dans le message. Si tu ne le trouves pas, demande-le avant de continuer.

    Procède toujours ainsi :
    1. Appelle fetch_medication_doc(cis) pour télécharger la fiche et obtenir la table des matières.
    2. Identifie les sections pertinentes pour répondre à la question.
    3. Appelle read_section(tab, section_id) pour chaque section utile.
       - Pour la posologie, les contre-indications, les effets indésirables : utilise l'onglet "rcp"
       - Pour les informations destinées au patient (notice) : utilise l'onglet "notice"
       - Pour les informations générales (indications, composition) : utilise l'onglet "fiche-info"
       - Pour les recommandations de bon usage (HAS, ANSM...) : utilise l'onglet "bon-usage"
    4. Synthétise une réponse claire et précise basée uniquement sur le contenu officiel.

    Ne fabrique pas d'informations. Si une section ne contient pas la réponse, consultes-en une autre.
    """,
    tools=[fetch_medication_doc, read_section],
)
