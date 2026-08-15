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
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Hermes 3.6 Enterprise Core</title>
    <script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background-color: #080c14; color: #f1f5f9; display: flex; justify-content: center; align-items: center; min-height: 100vh; padding: 15px; }
        .app-container { width: 100%; max-width: 1100px; height: 92vh; background: #0f172a; border: 1px solid #1e293b; border-radius: 12px; display: flex; flex-direction: column; overflow: hidden; box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.7); }
        .header { display: flex; justify-content: space-between; align-items: center; padding: 16px 24px; background: #131c31; border-bottom: 1px solid #1e293b; }
        .brand { display: flex; align-items: center; gap: 10px; font-size: 1.15rem; font-weight: 700; color: #38bdf8; }
        .header-right { display: flex; align-items: center; gap: 12px; }
        .status-badge { background: #064e3b; color: #34d399; border: 1px solid #059669; padding: 6px 14px; border-radius: 20px; font-size: 0.8rem; font-weight: 600; display: flex; align-items: center; gap: 6px; }
        .reset-btn { background: #ef4444; color: white; border: none; padding: 8px 16px; border-radius: 6px; font-size: 0.85rem; font-weight: 600; cursor: pointer; transition: 0.2s; }
        .reset-btn:hover { background: #dc2626; }
        .chat-box { flex: 1; padding: 24px; overflow-y: auto; display: flex; flex-direction: column; gap: 18px; background: #080c14; }
        .message { max-width: 90%; padding: 14px 18px; border-radius: 8px; font-size: 0.95rem; line-height: 1.6; }
        .user-msg { align-self: flex-end; background: #0284c7; color: #ffffff; border-bottom-right-radius: 2px; }
        .bot-msg { align-self: flex-start; width: 95%; background: #0f172a; border: 1px solid #1e293b; color: #f1f5f9; border-bottom-left-radius: 2px; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.3); }
        .bot-msg h1, .bot-msg h2, .bot-msg h3 { color: #38bdf8; margin: 12px 0 8px 0; border-bottom: 1px solid #334155; padding-bottom: 4px; }
        .bot-msg ul, .bot-msg ol { margin: 8px 0 8px 20px; }
        .bot-msg p { margin-bottom: 8px; }
        .bot-msg pre { background: #020617; padding: 14px; border-radius: 6px; overflow-x: auto; margin: 12px 0; border: 1px solid #1e293b; font-family: "Fira Code", monospace, sans-serif; }
        
        .bot-msg table { width: 100%; border-collapse: collapse; margin: 12px 0; font-size: 0.85rem; }
        .bot-msg th, .bot-msg td { border: 1px solid #334155; padding: 8px 12px; text-align: left; }
        .bot-msg th { background: #131c31; color: #38bdf8; font-weight: 700; border-bottom: 2px solid #0284c7; }
        .bot-msg tr:nth-child(even) { background: rgba(255, 255, 255, 0.02); }

        .bot-msg code { background: #020617; padding: 2px 6px; border-radius: 4px; font-family: monospace; color: #38bdf8; }
        .bot-msg pre code { background: transparent; padding: 0; color: #e2e8f0; }
        .input-area { padding: 18px 24px; background: #0f172a; border-top: 1px solid #1e293b; display: flex; gap: 12px; }
        .input-area input { flex: 1; background: #1e293b; border: 1px solid #334155; border-radius: 8px; padding: 12px 18px; color: white; font-size: 0.95rem; outline: none; }
        .input-area input:focus { border-color: #0284c7; }
        .send-btn { background: #0284c7; color: white; border: none; padding: 12px 26px; border-radius: 8px; font-weight: 600; cursor: pointer; transition: 0.2s; }
        .send-btn:hover { background: #0369a1; }
    </style>
</head>
<body>
    <div class="app-container">
        <div class="header">
            <div class="brand">
                <span>🤖</span> Hermes 3.6 Enterprise Core
            </div>
            <div class="header-right">
                <div class="status-badge">
                    <span>🟢</span> Web + Python + Memory Active
                </div>
                <button class="reset-btn" onclick="resetMemory()">🗑️ Resetar Memória</button>
            </div>
        </div>
        <div class="chat-box" id="chatBox"></div>
        <div class="input-area">
            <input type="text" id="msgInput" placeholder="Hermes, crie um Agente Especialista..." onkeypress="if(event.key==='Enter')sendMsg()">
            <button class="send-btn" onclick="sendMsg()">Enviar</button>
        </div>
    </div>
    <script>
        function appendMsg(role, text) {
            const box = document.getElementById('chatBox');
            const div = document.createElement('div');
            div.className = `message ${role}-msg`;
            if (role === 'bot') {
                div.innerHTML = marked.parse(text);
            } else {
                div.innerText = text;
            }
            box.appendChild(div);
            box.scrollTop = box.scrollHeight;
        }

        async function sendMsg() {
            const input = document.getElementById('msgInput');
            const text = input.value.trim();
            if (!text) return;
            appendMsg('user', text);
            input.value = '';
            
            try {
                const res = await fetch('/api/chat', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ message: text, project_id: 'default_project' })
                });
                const data = await res.json();
                const reply = data.reply || data.response || (typeof data === 'string' ? data : JSON.stringify(data));
                appendMsg('bot', reply);
            } catch(e) {
                appendMsg('bot', '**Erro:** Falha na comunicação com o servidor.');
            }
        }

        async function resetMemory() {
            if (confirm('Deseja realmente resetar a memória da conversa?')) {
                document.getElementById('chatBox').innerHTML = '';
                try {
                    await fetch('/api/reset', { method: 'POST' });
                } catch(e) {}
                appendMsg('bot', '🧹 **Memória resetada com sucesso!**');
            }
        }
    </script>
</body>
</html>"""

