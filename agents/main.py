from __future__ import annotations

from dotenv import load_dotenv
load_dotenv()

import os
import uvicorn
from fastapi import FastAPI
from ag_ui_adk import ADKAgent, add_adk_fastapi_endpoint

from orchestrator.agent import root_agent

adk_orchestrator_agent = ADKAgent(
    adk_agent=root_agent,
    app_name="orchestrator_app",
    user_id="demo_user",
    session_timeout_seconds=3600,
    use_in_memory_services=True,
)

app = FastAPI(title="medokchat — Orchestrateur (ADK + AG-UI)")
add_adk_fastapi_endpoint(app, adk_orchestrator_agent, path="/")

if __name__ == "__main__":
    port = int(os.getenv("ORCHESTRATOR_PORT", 9000))
    print(f"Starting orchestrator on http://localhost:{port}")
    uvicorn.run(app, host="0.0.0.0", port=port)
