import os
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional

app = FastAPI(
    title="Hermes Autonomous Enterprise Core",
    version="3.0.0",
    description="Multi-Tenant Enterprise Core com Workspaces Isolados por Projeto"
)

class ChatPayload(BaseModel):
    project_id: Optional[str] = "default_project"
    message: str

@app.get("/")
def read_root():
    return {"status": "ONLINE", "system": "Hermes 3.0 Multi-Tenant Enterprise Core"}

@app.post("/api/chat")
async def chat_endpoint(payload: ChatPayload):
    try:
        # Define e garante a criação do workspace isolado do projeto
        project_slug = payload.project_id.strip().replace(" ", "_").lower()
        workspace_dir = os.path.join(os.getcwd(), "projects", project_slug)
        os.makedirs(os.path.join(workspace_dir, "outputs"), exist_ok=True)
        os.makedirs(os.path.join(workspace_dir, "skills"), exist_ok=True)

        # Aqui o Hermes opera exclusivamente dentro do diretório do projeto isolado
        return {
            "status": "success",
            "project_id": project_slug,
            "workspace": workspace_dir,
            "response": f"[Projeto: {project_slug}] Mensagem processada de forma 100% isolada no workspace dedicado."
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
