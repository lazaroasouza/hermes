from fastapi import FastAPI
app = FastAPI()
﻿from fastapi.responses import HTMLResponse

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