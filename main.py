import os
import asyncio
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel
from google import genai

app = FastAPI(title="Hermes Autonomous Agent Core", version="1.0.0")

# Captura flexível da chave no Render
api_key = (
    os.getenv("GEMINI_API_KEY") or
    os.getenv("Gemini API Key") or
    os.getenv("gemini_api_key")
)

client = genai.Client(api_key=api_key.strip()) if api_key else None

class ChatPayload(BaseModel):
    message: str

def get_active_model_name():
    """Consulta o Google AI Studio para descobrir dinamicamente os modelos disponíveis."""
    if not client:
        return "gemini-2.5-flash"
    
    try:
        models = list(client.models.list())
        model_names = [
            m.name.replace("models/", "") if hasattr(m, "name") else str(m)
            for m in models
        ]
        
        # 1. Tenta encontrar um modelo 'flash' ativo
        flash_models = [m for m in model_names if "flash" in m]
        if flash_models:
            return flash_models[0]
            
        # 2. Caso não ache flash, pega o primeiro disponível
        if model_names:
            return model_names[0]
            
    except Exception as e:
        print(f"Erro ao listar modelos automaticamente: {e}")
        
    return "gemini-2.5-flash"

@app.get("/", response_class=HTMLResponse)
def read_root():
    return "<h3>Hermes API está online com Gemini! Acesse <a href='/chat' style='color:#3b82f6;'>/chat</a> para interagir.</h3>"

@app.post("/api/chat")
async def chat_endpoint(payload: ChatPayload):
    user_msg = payload.message

    if not client:
        return JSONResponse(content={
            "status": "error",
            "reply": "⚠️ GEMINI_API_KEY não foi configurada nas variáveis de ambiente do Render."
        })

    # Seleção dinâmica do modelo disponível
    active_model = get_active_model_name()

    try:
        response = await asyncio.to_thread(
            client.models.generate_content,
            model=active_model,
            contents=user_msg,
        )
        bot_reply = response.text if response.text else "Não foi possível obter resposta."
        return JSONResponse(content={"status": "success", "reply": bot_reply})
        
    except Exception as e:
        return JSONResponse(content={
            "status": "error",
            "reply": f"Erro na API do Gemini (tentando modelo '{active_model}'): {str(e)}"
        })

@app.get("/chat", response_class=HTMLResponse)
async def get_chat_ui():
    html_content = """<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Hermes Autonomous Agent</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; font-family: 'Segoe UI', system-ui, sans-serif; }
        body { background-color: #0f172a; color: #f8fafc; display: flex; flex-direction: column; height: 100vh; justify-content: center; align-items: center; }
        .chat-container { width: 90%; max-width: 850px; height: 85vh; background-color: #1e293b; border-radius: 12px; display: flex; flex-direction: column; box-shadow: 0 10px 25px rgba(0,0,0,0.5); border: 1px solid #334155; }
        .chat-header { padding: 20px; background-color: #0f172a; border-bottom: 1px solid #334155; border-top-left-radius: 12px; border-top-right-radius: 12px; display: flex; align-items: center; justify-content: space-between; }
        .chat-header h2 { color: #38bdf8; font-size: 1.25rem; font-weight: 600; }
        .chat-box { flex: 1; padding: 20px; overflow-y: auto; display: flex; flex-direction: column; gap: 15px; }
        .message { padding: 12px 16px; border-radius: 8px; max-width: 80%; line-height: 1.5; font-size: 0.95rem; word-break: break-word; white-space: pre-wrap; }
        .user-msg { background-color: #0284c7; color: #fff; align-self: flex-end; border-bottom-right-radius: 2px; }
        .bot-msg { background-color: #334155; color: #f1f5f9; align-self: flex-start; border-bottom-left-radius: 2px; }
        .status-msg { background-color: rgba(56, 189, 248, 0.1); color: #38bdf8; border: 1px dashed #0284c7; align-self: flex-start; font-size: 0.85rem; font-style: italic; }
        .chat-input-area { padding: 15px; background-color: #0f172a; border-top: 1px solid #334155; display: flex; gap: 10px; border-bottom-left-radius: 12px; border-bottom-right-radius: 12px; }
        input[type="text"] { flex: 1; padding: 12px 16px; background-color: #1e293b; border: 1px solid #475569; border-radius: 6px; color: #fff; outline: none; font-size: 0.95rem; }
        input[type="text"]:focus { border-color: #38bdf8; }
        button { padding: 12px 24px; background-color: #0284c7; border: none; border-radius: 6px; color: #fff; font-weight: 600; cursor: pointer; transition: background-color 0.2s; }
        button:hover { background-color: #0369a1; }
        button:disabled { background-color: #475569; cursor: not-allowed; }
    </style>
</head>
<body>
    <div class="chat-container">
        <div class="chat-header">
            <h2>🤖 Hermes Autonomous Agent Core (Gemini AI)</h2>
        </div>
        <div class="chat-box" id="chatBox">
            <div class="message bot-msg">Olá! Sou o Hermes. Como posso te ajudar hoje?</div>
        </div>
        <div class="chat-input-area">
            <input type="text" id="userInput" placeholder="Digite sua mensagem..." onkeydown="if(event.key==='Enter') sendMessage()">
            <button id="sendBtn" onclick="sendMessage()">Enviar</button>
        </div>
    </div>

    <script>
        async function sendMessage() {
            const input = document.getElementById('userInput');
            const chatBox = document.getElementById('chatBox');
            const sendBtn = document.getElementById('sendBtn');
            const text = input.value.trim();
            if (!text) return;

            const userDiv = document.createElement('div');
            userDiv.className = 'message user-msg';
            userDiv.textContent = text;
            chatBox.appendChild(userDiv);
            
            input.value = '';
            input.disabled = true;
            sendBtn.disabled = true;
            chatBox.scrollTop = chatBox.scrollHeight;

            const statusDiv = document.createElement('div');
            statusDiv.className = 'message status-msg';
            statusDiv.textContent = '🧠 Processando resposta...';
            chatBox.appendChild(statusDiv);
            chatBox.scrollTop = chatBox.scrollHeight;

            try {
                const response = await fetch('/api/chat', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ message: text })
                });

                const data = await response.json();
                statusDiv.remove();

                const botDiv = document.createElement('div');
                botDiv.className = 'message bot-msg';
                botDiv.textContent = data.reply;
                chatBox.appendChild(botDiv);

            } catch (err) {
                statusDiv.remove();
                const errorDiv = document.createElement('div');
                errorDiv.className = 'message bot-msg';
                errorDiv.style.color = '#f87171';
                errorDiv.textContent = 'Erro ao se comunicar com o servidor Hermes.';
                chatBox.appendChild(errorDiv);
            } finally {
                input.disabled = false;
                sendBtn.disabled = false;
                input.focus();
                chatBox.scrollTop = chatBox.scrollHeight;
            }
        }
    </script>
</body>
</html>"""
    return HTMLResponse(content=html_content)