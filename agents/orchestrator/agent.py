import os
from typing import Optional

from google.adk import Agent
from google.adk.agents.callback_context import CallbackContext
from google.adk.models import LiteLlm
from google.genai import types

from context_filter import keep_orchestrator_context
from med_finder.agent import root_agent as med_finder_agent
from med_documentation.agent import root_agent as med_documentation_agent


def _before_agent_callback(callback_context: CallbackContext) -> Optional[types.Content]:
    if "current_med" not in callback_context.state:
        callback_context.state["current_med"] = "Aucun médicament sélectionné pour cette session."
    return None

root_agent = Agent(
    model=LiteLlm(
        model=f'anthropic/{os.getenv("LLM_MODEL_NAME")}',
        api_key=os.getenv("ANTHROPIC_API_KEY"),
        stream=True,
    ),
    name="orchestrator",
    description="Main orchestrator for medokchat",
    instruction="""
    You are the medical assistant for medokchat.

    Current medication for this session:
    {current_med}

    Available agents:
    - **med_finder**: identifies a medication in the ANSM database → returns CIS, name, form, routes, status, active substances.
    - **med_documentation**: reads the official medication file (RCP, notice, bon usage) from the CIS.
      Covers: dosage, contraindications, side effects, interactions, pregnancy, patient leaflet, HAS/ANSM recommendations.

    Sequence:
    1. If the requested medication is already in "Current medication" above, use its CIS directly — do not call med_finder again.
    2. Otherwise, call med_finder to identify the medication.
    3. For any clinical question (dosage, contraindications, side effects, interactions, notice…), call med_documentation.

    All your answers rely solely on what the agents return to you.
    Never call agents simultaneously. To switch the current medication, use **med_finder**.
    """,
    sub_agents=[med_finder_agent, med_documentation_agent],
    before_agent_callback=_before_agent_callback,
    before_model_callback=keep_orchestrator_context,
)
