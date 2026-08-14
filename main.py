from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
from typing import Dict, Any
import json
import os

from app.skills.terminal_skill import run_powershell_command
from app.core.llm import llm_engine
from app.core.db import clear_history, get_history
from app.mcp.manager import mcp_hub

app = FastAPI(title="Hermes Autonomous Agent Core")

if os.path.exists("app/static"):
    app.mount("/static", StaticFiles(directory="app/static"), name="static")

class AgentRequest(BaseModel):
    user_input: str
    session_id: str = "default-session"
    role: str = "architect"

@app.get("/")
async def root():
    if os.path.exists("app/static/index.html"):
        return FileResponse("app/static/index.html")
    return {
        "status": "active",
        "agent": "Hermes Multi-Agent Core",
        "mcp": await mcp_hub.get_status()
    }

@app.get("/chat")
async def chat_ui():
    if os.path.exists("app/static/index.html"):
        return FileResponse("app/static/index.html")
    return JSONResponse(status_code=404, content={"message": "Interface Web não encontrada"})

@app.get("/api/v1/hermes/history/{session_id}")
async def fetch_history(session_id: str):
    return {"session_id": session_id, "history": get_history(session_id)}

@app.delete("/api/v1/hermes/history/{session_id}/clear")
async def delete_history(session_id: str):
    clear_history(session_id)
    return {"status": "cleared", "session_id": session_id}

@app.post("/api/v1/hermes/chat")
async def hermes_agent_endpoint(request: AgentRequest):
    user_text = request.user_input.lower()

    if user_text.startswith("execute "):
        command_to_run = request.user_input[8:].strip()
        result = await run_powershell_command(command_to_run)
        return {
            "session_id": request.session_id,
            "agent": "Hermes Direct Execution",
            "provider_used": "Direct Terminal Skill",
            "status": "completed",
            "role_active": request.role,
            "response": f"Comando '{command_to_run}' executado:\n\n{result['stdout']}",
            "execution_trace": [{"role": "user", "content": request.user_input}, {"role": "tool", "name": "run_powershell_command", "content": json.dumps(result)}]
        }

    llm_result = await llm_engine.process_chat(request.user_input, request.session_id, active_role=request.role)
    return {
        "session_id": request.session_id,
        "agent": "Hermes Core",
        "provider_used": llm_result["provider_used"],
        "role_active": llm_result["role_active"],
        "status": "completed",
        "response": llm_result["response"],
        "execution_trace": llm_result["execution_trace"]
    }
