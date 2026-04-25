import os
from google.adk import Agent
from google.adk.models import LiteLlm

from context_filter import keep_orchestrator_context
from .tools import fetch_medication_doc, read_section

root_agent = Agent(
    model=LiteLlm(
        model=f'anthropic/{os.getenv("LLM_MODEL_NAME")}',
        api_key=os.getenv("ANTHROPIC_API_KEY"),
        stream=True,
    ),
    name="med_documentation",
    description="Reads and navigates the official medication file (RCP, notice, bon usage) from its CIS",
    instruction="""
    You receive a question about a medication.

    Current medication for this session:
    {current_med}

    The medication CIS is in "Current medication" above (line "CIS : ...").

    Always proceed as follows:
    1. Call fetch_medication_doc(cis) with the CIS above to download the file and get the table of contents.
    2. Identify the relevant sections to answer the question.
    3. Call read_section(tab, section_id) for each useful section:
       - dosage, contraindications, side effects, interactions → tab "rcp"
       - patient information → tab "notice"
       - indications, composition → tab "fiche-info"
       - HAS/ANSM recommendations → tab "bon-usage"
    4. Synthesize a clear answer based solely on the official content retrieved.

    If a section does not contain the answer, explore other sections before concluding.
    """,
    tools=[fetch_medication_doc, read_section],
    before_model_callback=keep_orchestrator_context,

)
