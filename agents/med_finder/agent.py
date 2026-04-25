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
    description="Identifies a medication in the official French database (ANSM) and returns its CIS",
    instruction="""
    Your sole objective: identify the medication in the ANSM database and call select_med with its CIS.
    Every time you are called, it is to find the CIS of a medication — nothing else.

    Procedure:
    1. Call search_medicaments with the medication name (name only, no dosage or form).
       Up to 5 attempts — start specific, broaden if no results.
    2. Select the most relevant result:
       - Best match with the request
       - Status "Commercialisée" preferred
       - Matching pharmaceutical form if specified
    3. Call select_med(cis) with the CIS of the chosen medication.

    ABSOLUTE RULE: you must always finish by calling select_med.
    If no medication is found after 5 attempts, stop without calling select_med.
    """,
    tools=[search_medicaments, select_med],
    before_model_callback=keep_orchestrator_context,
)
