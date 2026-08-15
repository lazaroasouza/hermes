import os
import json
import subprocess
import sys
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any

app = FastAPI(
    title="Hermes 3.0 Enterprise Core",
    version="3.2.0",
    description="Core Híbrido com Motor de Execução de Código Isolado por Projeto"
)

class TaskPayload(BaseModel):
    project_id: Optional[str] = "default_project"
    code: str  # Código Python a ser executado de forma autônoma no workspace

@app.get("/")
def read_root():
    env_type = "Render Cloud" if os.getenv("RENDER") else "Local Machine (Offline Ready)"
    return {"status": "ONLINE", "environment": env_type, "version": "3.2.0"}

@app.post("/api/execute")
async def execute_task(payload: TaskPayload):
    try:
        # 1. Configura o Workspace isolado
        project_slug = payload.project_id.strip().replace(" ", "_").lower()
        workspace_dir = os.path.join(os.getcwd(), "projects", project_slug)
        os.makedirs(workspace_dir, exist_ok=True)

        # 2. Salva o código enviado em um script temporário dentro do workspace
        script_path = os.path.join(workspace_dir, "task_execution.py")
        with open(script_path, "w", encoding="utf-8") as f:
            f.write(payload.code)

        # 3. Executa o código em subprocesso apontando o diretório de trabalho para o workspace
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
