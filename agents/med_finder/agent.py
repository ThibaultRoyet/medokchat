import os
import re
from typing import Optional

from google.adk import Agent
from google.adk.agents.callback_context import CallbackContext
from google.adk.models import LiteLlm
from google.adk.models.llm_response import LlmResponse
from google.genai import types

from context_filter import keep_last_invocation
from .tools import search_medicaments


def _after_model_callback(
    callback_context: CallbackContext,
    llm_response: LlmResponse,
) -> Optional[LlmResponse]:
    """Détecte le choix du LLM et enregistre le médicament complet en state."""
    if not llm_response.content or not llm_response.content.parts:
        return None

    full_text = "".join(
        part.text
        for part in llm_response.content.parts
        if hasattr(part, "text") and part.text
    )
    if not full_text:
        return None

    match = re.search(r"CHOIX_CIS:\s*(\d+)", full_text)
    if not match:
        return None

    cis = match.group(1)
    cache: dict = callback_context.state.get("_med_search_results", {})
    if cis in cache:
        callback_context.state["med_informations"] = cache[cis]

    return None


def _after_agent_callback(
    callback_context: CallbackContext,
) -> Optional[types.Content]:
    """Retourne l'intégralité des informations du médicament choisi comme output final."""
    med = callback_context.state.get("med_informations")
    if not med:
        return None

    substances = [
        f"{s['denominationSubstance']} {s.get('dosage', '')}".strip()
        for s in (med.get("composition") or [])
        if s.get("natureComposant") == "SA"
    ]

    lines = [
        f"CIS : {med.get('cis', 'N/A')}",
        f"Nom : {med.get('elementPharmaceutique', 'N/A')}",
        f"Forme : {med.get('formePharmaceutique', 'N/A')}",
        f"Voies : {', '.join(med.get('voiesAdministration') or [])}",
        f"Statut : {med.get('etatComercialisation', 'N/A')}",
        f"Substances actives : {', '.join(substances) if substances else 'N/A'}",
    ]

    return types.Content(
        role="model",
        parts=[types.Part(text="\n".join(lines))],
    )


root_agent = Agent(
    model=LiteLlm(
        model=f'anthropic/{os.getenv("LLM_MODEL_NAME")}',
        api_key=os.getenv("ANTHROPIC_API_KEY"),
    ),
    mode="task",
    name="med_finder",
    description="Identifie un médicament dans la base officielle française (ANSM) et retourne son CIS",
    instruction="""
    En tant qu'agent Task suis les instruction pour remplir ton objectif et l'agent supérieur s'occupera de continué le travail.
    Ton unique objectif est donc d'identifier le médicament demandé dans la base ANSM et de retourner son CIS.
    Tu ne donnes pas de conseils médicaux ni d'informations sur le médicament — tu trouves uniquement le document.

    Procédure :
    1. Appelle search_medicaments avec le nom du médicament.
       Tu peux faire jusqu'à 5 recherches pour trouver le medicament, tu peux commencer par des requête spécifique et ensuite rendre ta requête plus large (moins de mots ou plus générique).
    2. Choisis le résultat le plus pertinent :
       - Correspondance maximale avec la demande
       - Statut "Commercialisée" préférable
       - Forme pharmaceutique adaptée si précisée
    3. Termine OBLIGATOIREMENT ta réponse par (sans rien après) :
       CHOIX_CIS: <le CIS du médicament choisi>

    Une fois le CHOIX_CIS émis, ton travail est terminé. Retourne immédiatement le contrôle à l'orchestrateur — ne pose pas de questions, n'ajoute aucun commentaire.
    """,
    tools=[search_medicaments],
    before_model_callback=keep_last_invocation,
    after_model_callback=_after_model_callback,
    after_agent_callback=_after_agent_callback,
)
