import os
import re
from typing import Optional

from google.adk import Agent
from google.adk.agents.callback_context import CallbackContext
from google.adk.models import LiteLlm
from google.adk.models.llm_response import LlmResponse
from google.genai import types

from context_filter import keep_orchestrator_context
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

    match = re.search(r"<cis_selected>\s*(\d+)\s*</cis_selected>", full_text)
    if not match:
        return None

    cis = match.group(1)
    if cis == "non_trouvé":
        return None

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

    text = "\n".join(lines)
    callback_context.state["current_med"] = text

    return types.Content(
        role="model",
        parts=[types.Part(text=text)],
    )


root_agent = Agent(
    model=LiteLlm(
        model=f'anthropic/{os.getenv("LLM_MODEL_NAME")}',
        api_key=os.getenv("ANTHROPIC_API_KEY"),
    ),
    name="med_finder",
    description="Identifie un médicament dans la base officielle française (ANSM) et retourne son CIS",
    instruction="""
    Ton unique objectif : identifier le médicament dans la base ANSM et signaler son CIS via la balise obligatoire.

    Procédure :
    1. Appelle search_medicaments avec le nom du médicament (nom seul, sans dosage ni forme).
       Jusqu'à 5 tentatives — commence spécifique, élargis si aucun résultat.
    2. Sélectionne le résultat le plus pertinent :
       - Correspondance maximale avec la demande
       - Statut "Commercialisée" préférable
       - Forme pharmaceutique adaptée si précisée
    3. Dès que tu as sélectionné le médicament, tu DOIS inclure cette balise dans ta réponse :
       <cis_selected>LE_CIS_ICI</cis_selected>

    RÈGLE ABSOLUE : ta réponse finale doit toujours contenir <cis_selected>...</cis_selected>.
    Sans cette balise, ta réponse est considérée comme invalide.
    Si aucun médicament n'est trouvé après 5 tentatives, réponds : <cis_selected>non_trouvé</cis_selected>
    """,
    tools=[search_medicaments],
    before_model_callback=keep_orchestrator_context,
    after_model_callback=_after_model_callback,
    after_agent_callback=_after_agent_callback,
)
