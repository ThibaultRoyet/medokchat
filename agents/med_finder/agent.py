import os

from google.adk import Agent
from google.adk.models import LiteLlm

root_agent = Agent(
    model=LiteLlm(
        model=f'anthropic/{os.getenv("LLM_MODEL_NAME")}',
    ),
    name="med finder",
    description="med finder agent",
    instruction="""
    Selon tes connaissance devine le nom du medicament
    """
)