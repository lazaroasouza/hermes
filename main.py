import os
import asyncio
import sqlite3
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel
from google import genai
from google.genai import types

app = FastAPI(title="Hermes Autonomous Agent Core", version="2.0.0")

# Captura flexível da chave no Render
api_key = (
    os.getenv("GEMINI_API_KEY") or
    os.getenv("Gemini API Key") or
    os.getenv("gemini_api_key")
)

client = genai.Client(api_key=api_key.strip()) if api_key else None

DB_PATH = "hermes_memory.db"

# --- BANCO DE DADOS & MEMÓRIA ---
def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

init_db()

def save_message(role: str, content: str):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO messages (role, content) VALUES (?, ?)", (role, content))
    conn.commit()
    conn.close()

def get_history_for_gemini(limit: int = 12):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT role, content FROM messages ORDER BY id DESC LIMIT ?", (limit,))
    rows = cursor.fetchall()
    conn.close()
    
    history = []
    for role, content in reversed(rows):
        history.append(types.Content(
            role=role,
            parts=[types.Part.from_text(text=content)]
        ))
    return history

def get_history_for_ui():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT role, content FROM messages ORDER BY id ASC")
    rows = cursor.fetchall()
    conn.close()
    return [{"role": r[0], "content": r[1]} for r in rows]

def clear_db_history():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM messages")
    conn.commit()
    conn.close()

# --- FERRAMENTA DE BUSCA WEB ---
def web_search(query: str) -> str:
    """Pesquisa na web por informações atualizadas, notícias, documentações ou dados na internet."""
    try:
        from duckduckgo_search import DDGS
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=5))
            if not results:
                return "Nenhum resultado encontrado na web."
            formatted = []
            for r in results:
                formatted.append(f"Título: {r.get('title')}\nURL: {r.get('href')}\nResumo: {r.get('body')}")
            return "\n\n".join(formatted)
    except Exception as e:
        return f"Erro ao realizar pesquisa na web: {e}"

# --- PROMPT DE SISTEMA / PERSONALIDADE ---
SYSTEM_PROMPT = """Você é o Hermes, um Agente Autônomo de Inteligência Artificial de alta capacidade, analítico, eficiente e resolutivo.

Suas diretrizes fundamentais:
1. Responda de forma clara, estruturada, direta e profissional.
2. Você possui a ferramenta 'web_search' para consultar a internet. Use-a sempre que precisar de dados atualizados, cotações, notícias ou documentações técnicas.
3. Você mantém o histórico de conversas anteriores com o usuário para garantir continuidade no raciocínio.
4. Caso resolva problemas de programação ou sistemas, forneça códigos completos e prontos para execução.
"""

class ChatPayload(BaseModel):
    message: str

@app.get("/", response_class=HTMLResponse)
def read_root():
    return "<h3>Hermes API 2.0 está online! Acesse <a href='/chat' style='color:#3b82f6;'>/chat</a> para interagir.</h3>"

@app.get("/api/history")
def get_history():
    return JSONResponse(content={"status": "success", "history": get_history_for_ui()})

@app.delete("/api/history")
def clear_history():
    clear_db_history()
    return JSONResponse(content={"status": "success", "message": "Memória limpa com sucesso."})

@app.post("/api/chat")
async def chat_endpoint(payload: ChatPayload):
    user_msg = payload.message.strip()
    if not user_msg:
        return JSONResponse(content={"status": "error", "reply": "Mensagem vazia."})

    if not client:
        return JSONResponse(content={
            "status": "error",
            "reply": "⚠️ GEMINI_API_KEY não foi configurada nas variáveis de ambiente do Render."
        })

    # Salva mensagem do usuário na memória
    save_message("user", user_msg)

    # Identificação dinâmica de modelos disponíveis
    candidate_models = []
    try:
        models_page = client.models.list()
        for m in models_page:
            name = m.name.replace("models/", "") if hasattr(m, "name") else str(m)
            if "gemini" in name.lower() and not any(x in name.lower() for x in ["embed", "imagen", "aqa", "tts", "stt"]):
                candidate_models.append(name)
    except Exception as e:
        print(f"Aviso ao listar modelos: {e}")

    defaults = ["gemini-2.5-flash", "gemini-2.0-flash", "gemini-1.5-flash"]
    for d in defaults:
        if d not in candidate_models:
            candidate_models.append(d)

    # Carrega histórico para o contexto
    history_contents = get_history_for_gemini(limit=10)

    config = types.GenerateContentConfig(
        system_instruction=SYSTEM_PROMPT,
        tools=[web_search],
        temperature=0.7
    )

    last_error = ""
    for model_name in candidate_models:
        try:
            response = await asyncio.to_thread(
                client.models.generate_content,
                model=model_name,
                contents=history_contents,
                config=config,
            )
            if response and response.text:
                bot_reply = response.text
                save_message("model", bot_reply)
                return JSONResponse(content={"status": "success", "reply": bot_reply})
        except Exception as e:
            last_error = str(e)
            print(f"Modelo '{model_name}' falhou ({e}). Tentando próximo...")
            continue

    return JSONResponse(content={
        "status": "error",
        "reply": f"Erro ao gerar resposta com o Gemini: {last_error}"
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
        .chat-container { width: 90%; max-width: 900px; height: 85vh; background-color: #1e293b; border-radius: 12px; display: flex; flex-direction: column; box-shadow: 0 10px 25px rgba(0,0,0,0.5); border: 1px solid #334155; }
        .chat-header { padding: 18px 24px; background-color: #0f172a; border-bottom: 1px solid #334155; border-top-left-radius: 12px; border-top-right-radius: 12px; display: flex; align-items: center; justify-content: space-between; }
        .chat-header h2 { color: #38bdf8; font-size: 1.25rem; font-weight: 600; }
        .clear-btn { padding: 6px 14px; background-color: #ef4444; color: #fff; border: none; border-radius: 6px; font-size: 0.82rem; font-weight: 600; cursor: pointer; transition: background-color 0.2s; }
        .clear-btn:hover { background-color: #dc2626; }
        .chat-box { flex: 1; padding: 20px; overflow-y: auto; display: flex; flex-direction: column; gap: 15px; }
        .message { padding: 12px 16px; border-radius: 8px; max-width: 80%; line-height: 1.5; font-size: 0.95rem; word-break: break-word; white-space: pre-wrap; }
        .user-msg { background-color: #0284c7; color: #fff; align-self: flex-end; border-bottom-right-radius: 2px; }
        .bot-msg { background-color: #334155; color: #f1f5f9; align-self: flex-start; border-bottom-left-radius: 2px; }
        .status-msg { background-color: rgba(56, 189, 248, 0.1); color: #38bdf8; border: 1px dashed #0284c7; align-self: flex-start; font-size: 0.85rem; font-style: italic; }
        .chat-input-area { padding: 15px; background-color: #0f172a; border-top: 1px solid #334155; display: flex; gap: 10px; border-bottom-left-radius: 12px; border-bottom-right-radius: 12px; }
        input[type="text"] { flex: 1; padding: 12px 16px; background-color: #1e293b; border: 1px solid #475569; border-radius: 6px; color: #fff; outline: none; font-size: 0.95rem; }
        input[type="text"]:focus { border-color: #38bdf8; }
        button.send-btn { padding: 12px 24px; background-color: #0284c7; border: none; border-radius: 6px; color: #fff; font-weight: 600; cursor: pointer; transition: background-color 0.2s; }
        button.send-btn:hover { background-color: #0369a1; }
        button:disabled { background-color: #475569; cursor: not-allowed; }
    </style>
</head>
<body>
    <div class="chat-container">
        <div class="chat-header">
            <h2>🤖 Hermes Autonomous Agent Core (Web + Memória)</h2>
            <button class="clear-btn" onclick="clearMemory()">🗑️ Limpar Memória</button>
        </div>
        <div class="chat-box" id="chatBox">
            <div class="message bot-msg">Olá! Sou o Hermes. Estou conectado à web e com memória ativa. Como posso te ajudar hoje?</div>
        </div>
        <div class="chat-input-area">
            <input type="text" id="userInput" placeholder="Digite sua mensagem ou peça uma pesquisa na web..." onkeydown="if(event.key==='Enter') sendMessage()">
            <button class="send-btn" id="sendBtn" onclick="sendMessage()">Enviar</button>
        </div>
    </div>

    <script>
        async function loadHistory() {
            try {
                const res = await fetch('/api/history');
                const data = await res.json();
                if (data.status === 'success' && data.history.length > 0) {
                    const chatBox = document.getElementById('chatBox');
                    chatBox.innerHTML = '';
                    data.history.forEach(msg => {
                        const div = document.createElement('div');
                        div.className = `message ${msg.role === 'user' ? 'user-msg' : 'bot-msg'}`;
                        div.textContent = msg.content;
                        chatBox.appendChild(div);
                    });
                    chatBox.scrollTop = chatBox.scrollHeight;
                }
            } catch (err) {
                console.error("Erro ao carregar histórico:", err);
            }
        }

        async function clearMemory() {
            if (!confirm("Tem certeza que deseja apagar a memória da conversa?")) return;
            try {
                await fetch('/api/history', { method: 'DELETE' });
                const chatBox = document.getElementById('chatBox');
                chatBox.innerHTML = '<div class="message bot-msg">Memória limpa com sucesso. Como posso te ajudar agora?</div>';
            } catch (err) {
                alert("Erro ao limpar memória.");
            }
        }

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
            statusDiv.textContent = '🧠 [Hermes Core] Raciocinando e consultando web se necessário...';
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
                errorDiv.textContent = 'Erro de comunicação com o servidor Hermes.';
                chatBox.appendChild(errorDiv);
            } finally {
                input.disabled = false;
                sendBtn.disabled = false;
                input.focus();
                chatBox.scrollTop = chatBox.scrollHeight;
            }
        }

        // Carrega o histórico ao abrir a página
        window.onload = loadHistory;
    </script>
</body>
</html>"""
    return HTMLResponse(content=html_content)