import asyncio
import json
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, StreamingResponse
from pydantic import BaseModel

app = FastAPI(title="Hermes Autonomous Agent Core", version="0.1.0")

class ChatPayload(BaseModel):
    message: str

@app.get("/", response_class=HTMLResponse)
def read_root():
    return "<h3>Hermes API esta online! Acesse <a href='/chat' style='color:#3b82f6;'>/chat</a> para interagir.</h3>"

@app.post("/api/chat/stream")
async def chat_stream(payload: ChatPayload):
    async def event_generator():
        user_msg = payload.message
        
        yield f"data: {json.dumps({'type': 'status', 'content': '🧠 [Roteador] Analisando a instrucao recebida...'})}\n\n"
        await asyncio.sleep(1.2)
        
        yield f"data: {json.dumps({'type': 'status', 'content': '💻 [Dev Coder] Processando logica e estruturando o codigo...'})}\n\n"
        await asyncio.sleep(1.5)
        
        yield f"data: {json.dumps({'type': 'status', 'content': '🧪 [QA Tester] Executando verificacoes e testes de integridade...'})}\n\n"
        await asyncio.sleep(1.2)
        
        final_reply = f"Hermes processou com sucesso sua mensagem: '{user_msg}'."
        yield f"data: {json.dumps({'type': 'final', 'content': final_reply})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")

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
        .message { padding: 12px 16px; border-radius: 8px; max-width: 80%; line-height: 1.5; font-size: 0.95rem; word-break: break-word; }
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
            <h2>🤖 Hermes Autonomous Agent Core</h2>
        </div>
        <div class="chat-box" id="chatBox">
            <div class="message bot-msg">Olá! Sou o Hermes. Envie um comando para acompanhar minhas ações em tempo real!</div>
        </div>
        <div class="chat-input-area">
            <input type="text" id="userInput" placeholder="Digite sua mensagem ou instrução..." onkeydown="if(event.key==='Enter') sendMessage()">
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

            try {
                const response = await fetch('/api/chat/stream', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ message: text })
                });

                const reader = response.body.getReader();
                const decoder = new TextDecoder();
                let activeStatusDiv = null;

                while (true) {
                    const { value, done } = await reader.read();
                    if (done) break;

                    const chunk = decoder.decode(value);
                    const lines = chunk.split('\n');

                    for (const line of lines) {
                        if (line.startsWith('data: ')) {
                            const data = JSON.parse(line.replace('data: ', ''));

                            if (data.type === 'status') {
                                if (!activeStatusDiv) {
                                    activeStatusDiv = document.createElement('div');
                                    activeStatusDiv.className = 'message status-msg';
                                    chatBox.appendChild(activeStatusDiv);
                                }
                                activeStatusDiv.textContent = data.content;
                            } else if (data.type === 'final') {
                                if (activeStatusDiv) {
                                    activeStatusDiv.remove();
                                }
                                const botDiv = document.createElement('div');
                                botDiv.className = 'message bot-msg';
                                botDiv.textContent = data.content;
                                chatBox.appendChild(botDiv);
                            }
                            chatBox.scrollTop = chatBox.scrollHeight;
                        }
                    }
                }
            } catch (err) {
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