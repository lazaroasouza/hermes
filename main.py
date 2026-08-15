import os
import json
import logging
import subprocess
import sys
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any

app = FastAPI(
    title="Hermes 3.5 Enterprise Core - All-In-One",
    version="3.5.0",
    description="Core Híbrido Completo: Workspaces, Estado, Logging, Auto-Install e Sandbox Execution"
)

class ChatPayload(BaseModel):
    project_id: Optional[str] = "default_project"
    message: str
    metadata: Optional[Dict[str, Any]] = {}

class TaskPayload(BaseModel):
    project_id: Optional[str] = "default_project"
    code: str

def ensure_package(package_name: str):
    """Instala dependências dinamicamente se necessário."""
    try:
        __import__(package_name)
    except ImportError:
        subprocess.check_call([sys.executable, "-m", "pip", "install", package_name])

@app.get("/")
def read_root():
    env_type = "Render Cloud" if os.getenv("RENDER") else "Local Machine (Offline Ready)"
    return {
        "status": "ONLINE", 
        "environment": env_type, 
        "version": "3.5.0", 
        "modules": ["workspaces", "state_persistence", "auto_install", "sandbox_execution"]
    }

@app.post("/api/chat")
async def chat_endpoint(payload: ChatPayload):
    try:
        project_slug = payload.project_id.strip().replace(" ", "_").lower()
        workspace_dir = os.path.join(os.getcwd(), "projects", project_slug)
        outputs_dir = os.path.join(workspace_dir, "outputs")
        skills_dir = os.path.join(workspace_dir, "skills")
        
        os.makedirs(outputs_dir, exist_ok=True)
        os.makedirs(skills_dir, exist_ok=True)

        # Persistência de Estado do Projeto
        state_file = os.path.join(workspace_dir, "state.json")
        project_state = {}
        if os.path.exists(state_file):
            with open(state_file, "r", encoding="utf-8") as f:
                project_state = json.load(f)

        step_count = project_state.get("step_count", 0) + 1
        project_state["step_count"] = step_count
        project_state["last_message"] = payload.message

        with open(state_file, "w", encoding="utf-8") as f:
            json.dump(project_state, f, indent=2, ensure_ascii=False)

        # Auto-Logging do Projeto
        log_file = os.path.join(workspace_dir, "execution.log")
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(f"[PASSO {step_count}] Mensagem: {payload.message}\n")

        return {
            "status": "success",
            "environment": "Cloud" if os.getenv("RENDER") else "Local",
            "project_id": project_slug,
            "workspace": workspace_dir,
            "current_step": step_count,
            "response": f"[Projeto: {project_slug} | Passo: {step_count}] Processado com sucesso com persistência, log e isolamento."
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/execute")
async def execute_task(payload: TaskPayload):
    try:
        project_slug = payload.project_id.strip().replace(" ", "_").lower()
        workspace_dir = os.path.join(os.getcwd(), "projects", project_slug)
        os.makedirs(workspace_dir, exist_ok=True)

        script_path = os.path.join(workspace_dir, "task_execution.py")
        with open(script_path, "w", encoding="utf-8") as f:
            f.write(payload.code)

        process = subprocess.run(
            [sys.executable, script_path],
            cwd=workspace_dir,
            capture_output=True,
            text=True,
            timeout=30
        )

        return {
            "status": "success",
            "project_id": project_slug,
            "exit_code": process.returncode,
            "stdout": process.stdout,
            "stderr": process.stderr
        }
    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=408, detail="Tempo limite de execução excedido (Timeout 30s).")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
