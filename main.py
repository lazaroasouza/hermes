import os
import json
import logging
import subprocess
import sys
import requests
from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel
from typing import Optional, Dict, Any

app = FastAPI(
    title="Hermes 3.5 Enterprise Core - OmniChannel",
    version="3.6.0",
    description="Core Híbrido com Workspaces, Sandbox, Estado, Logging e Webhook de Telegram/WhatsApp"
)

# Token do Telegram Bot (Pode ser configurado via Variável de Ambiente no Render ou valor padrão)
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")

class ChatPayload(BaseModel):
    project_id: Optional[str] = "default_project"
    message: str
    metadata: Optional[Dict[str, Any]] = {}

class TaskPayload(BaseModel):
    project_id: Optional[str] = "default_project"
    code: str

@app.get("/")
def read_root():
    env_type = "Render Cloud" if os.getenv("RENDER") else "Local Machine (Offline Ready)"
    return {
        "status": "ONLINE", 
        "environment": env_type, 
        "version": "3.6.0", 
        "modules": ["workspaces", "state_persistence", "auto_install", "sandbox_execution", "omnichannel_telegram"]
    }

@app.post("/api/chat")
async def chat_endpoint(payload: ChatPayload):
    try:
        project_slug = payload.project_id.strip().replace(" ", "_").lower()
        workspace_dir = os.path.join(os.getcwd(), "projects", project_slug)
        os.makedirs(os.path.join(workspace_dir, "outputs"), exist_ok=True)
        os.makedirs(os.path.join(workspace_dir, "skills"), exist_ok=True)

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
            "response": f"[Projeto: {project_slug} | Passo: {step_count}] Processado via API Web."
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

@app.post("/api/webhook/telegram")
async def telegram_webhook(req: Request):
    """Recebe mensagens enviadas para o Bot do Telegram e responde automaticamente."""
    try:
        data = await req.json()
        if "message" in data:
            chat_id = data["message"]["chat"]["id"]
            text = data["message"].get("text", "")

            # Processa a mensagem usando o projeto padrão do Telegram
            response_text = f"🤖 Hermes 3.6 Core recebeu sua mensagem: '{text}'. Sistema operando na nuvem com sucesso!"

            # Se TELEGRAM_BOT_TOKEN estiver configurado, envia a resposta de volta ao Telegram
            if TELEGRAM_BOT_TOKEN:
                url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
                requests.post(url, json={"chat_id": chat_id, "text": response_text})

            return {"status": "ok", "received_text": text}
        return {"status": "ignored"}
    except Exception as e:
        return {"status": "error", "detail": str(e)}


from fastapi.responses import HTMLResponse

@app.get("/chat", response_class=HTMLResponse)
async def serve_chat_ui():
    return """<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <title>Hermes 3.6 - Chat UI</title>
    <style>
        body { font-family: Arial, sans-serif; background: #0f172a; color: #f8fafc; display: flex; justify-content: center; height: 100vh; margin: 0; align-items: center; }
        .chat-container { width: 450px; background: #1e293b; padding: 20px; border-radius: 12px; box-shadow: 0 4px 15px rgba(0,0,0,0.3); display: flex; flex-direction: column; height: 500px; }
        .chat-box { flex: 1; overflow-y: auto; border: 1px solid #334155; padding: 10px; border-radius: 8px; margin-bottom: 10px; background: #0f172a; }
        .input-group { display: flex; gap: 10px; }
        input { flex: 1; padding: 10px; border-radius: 6px; border: 1px solid #475569; background: #334155; color: #fff; }
        button { padding: 10px 15px; background: #3b82f6; color: #fff; border: none; border-radius: 6px; cursor: pointer; font-weight: 700; }
        button:hover { background: #2563eb; }
        .message { margin-bottom: 8px; padding: 6px 10px; border-radius: 6px; font-size: 14px; }
        .user-msg { background: #1e3a8a; text-align: right; }
        .bot-msg { background: #334155; }
    </style>
</head>
<body>
    <div class="chat-container">
        <h3>Hermes 3.6 - OmniChannel</h3>
        <div id="chatBox" class="chat-box"></div>
        <div class="input-group">
            <input type="text" id="msgInput" placeholder="Digite sua mensagem..." onkeypress="if(event.key==='Enter')sendMsg()">
            <button onclick="sendMsg()">Enviar</button>
        </div>
    </div>
    <script>
        async function sendMsg() {
            const t = document.getElementById('msgInput');
            const e = document.getElementById('chatBox');
            const s = t.value.trim();
            if (!s) return;
            e.innerHTML += `<div class="message user-msg"><b>Você:</b> ${s}</div>`;
            t.value = '';
            e.scrollTop = e.scrollHeight;
            try {
                const response = await fetch('/api/chat', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ message: s, project_id: 'default_project' })
                });
                const data = await response.json();
                const reply = data.reply || data.response || JSON.stringify(data);
                e.innerHTML += `<div class="message bot-msg"><b>Hermes:</b> ${reply}</div>`;
            } catch (err) {
                e.innerHTML += `<div class="message bot-msg" style="color:#f87171"><b>Erro:</b> Falha na comunicação.</div>`;
            }
            e.scrollTop = e.scrollHeight;
        }
    </script>
</body>
</html>"""
