from fastapi.responses import HTMLResponse

@app.get("/chat", response_class=HTMLResponse)
async def chat_ui():
    html_content = """
    <!DOCTYPE html>
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
            .chat-input-area { padding: 15px; background-color: #0f172a; border-top: 1px solid #334155; display: flex; gap: 10px; border-bottom-left-radius: 12px; border-bottom-right-radius: 12px; }
            input[type="text"] { flex: 1; padding: 12px 16px; background-color: #1e293b; border: 1px solid #475569; border-radius: 6px; color: #fff; outline: none; font-size: 0.95rem; }
            input[type="text"]:focus { border-color: #38bdf8; }
            button { padding: 12px 24px; background-color: #0284c7; border: none; border-radius: 6px; color: #fff; font-weight: 600; cursor: pointer; transition: background-color 0.2s; }
            button:hover { background-color: #0369a1; }
        </style>
    </head>
    <body>
        <div class="chat-container">
            <div class="chat-header">
                <h2>🤖 Hermes Autonomous Agent Core</h2>
            </div>
            <div class="chat-box" id="chatBox">
                <div class="message bot-msg">Olá! Sou o Hermes. Sistema Multi-Agente & Autocorreção (Self-Healing) ativo. Como posso te ajudar hoje?</div>
            </div>
            <div class="chat-input-area">
                <input type="text" id="userInput" placeholder="Digite sua mensagem ou instrução..." onkeydown="if(event.key==='Enter') sendMessage()">
                <button onclick="sendMessage()">Enviar</button>
            </div>
        </div>

        <script>
            async function sendMessage() {
                const input = document.getElementById('userInput');
                const chatBox = document.getElementById('chatBox');
                const text = input.value.trim();
                if (!text) return;

                const userDiv = document.createElement('div');
                userDiv.className = 'message user-msg';
                userDiv.textContent = text;
                chatBox.appendChild(userDiv);
                
                input.value = '';
                chatBox.scrollTop = chatBox.scrollHeight;

                try {
                    const response = await fetch('/api/chat', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ message: text })
                    });
                    const data = await response.json();

                    const botDiv = document.createElement('div');
                    botDiv.className = 'message bot-msg';
                    botDiv.textContent = data.response || data.message || JSON.stringify(data);
                    chatBox.appendChild(botDiv);
                } catch (err) {
                    const errorDiv = document.createElement('div');
                    errorDiv.className = 'message bot-msg';
                    errorDiv.style.color = '#f87171';
                    errorDiv.textContent = 'Erro de comunicação com o servidor Hermes.';
                    chatBox.appendChild(errorDiv);
                }
                
                chatBox.scrollTop = chatBox.scrollHeight;
            }
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)
