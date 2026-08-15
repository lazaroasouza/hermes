import os
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional

app = FastAPI(
    title="Hermes 3.0 Enterprise Core",
    version="3.0.0",
    description="Core Híbrido: Suporte Local (Offline) e Nuvem (Render)"
)

class ChatPayload(BaseModel):
    project_id: Optional[str] = "default_project"
    message: str

@app.get("/")
def read_root():
    # Detecta se está no Render ou em ambiente local
    env_type = "Render Cloud" if os.getenv("RENDER") else "Local Machine (Offline Ready)"
    return {"status": "ONLINE", "environment": env_type}

@app.post("/api/chat")
async def chat_endpoint(payload: ChatPayload):
    try:
        project_slug = payload.project_id.strip().replace(" ", "_").lower()
        workspace_dir = os.path.join(os.getcwd(), "projects", project_slug)
        os.makedirs(os.path.join(workspace_dir, "outputs"), exist_ok=True)
        os.makedirs(os.path.join(workspace_dir, "skills"), exist_ok=True)

        return {
            "status": "success",
            "environment": "Cloud" if os.getenv("RENDER") else "Local",
            "project_id": project_slug,
            "workspace": workspace_dir,
            "response": f"[Projeto: {project_slug}] Processado com sucesso no workspace isolado."
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
