import os
import sys
import io
import asyncio
import sqlite3
import contextlib
from datetime import datetime
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel
import httpx
from bs4 import BeautifulSoup
from google import genai
from google.genai import types

app = FastAPI(title="Hermes Autonomous Enterprise Core", version="3.0.0")

# Leitura flexível da API Key
api_key = (
    os.getenv("GEMINI_API_KEY") or
    os.getenv("Gemini API Key") or
    os.getenv("gemini_api_key")
)

client = genai.Client(api_key=api_key.strip()) if api_key else None
DB_PATH = "hermes_enterprise_memory.db"

# --- BANCO DE DADOS EM MODO WAL (ALTA VELOCIDADE) ---
def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("PRAGMA journal_mode=WAL;")
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

def get_history_for_gemini(limit: int = 16):
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

# --- FERRAMENTAS DO AGENTE (TOOLS) ---

def web_search(query: str) -> str:
    """Pesquisa no mecanismo de busca por informações atualizadas, cotações, notícias ou referências gerais."""
    try:
        from duckduckgo_search import DDGS
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=5))
            if not results:
                return "Nenhum resultado encontrado na busca."
            formatted = []
            for r in results:
                formatted.append(f"Título: {r.get('title')}\nURL: {r.get('href')}\nResumo: {r.get('body')}")
            return "\n\n".join(formatted)
    except Exception as e:
        return f"Erro na pesquisa web: {e}"

def fetch_webpage(url: str) -> str:
    """Acessa uma URL específica da internet e extrai todo o conteúdo textual da página."""
    try:
        with httpx.Client(timeout=10.0, follow_redirects=True) as http_client:
            resp = http_client.get(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
            if resp.status_code != 200:
                return f"Falha ao acessar URL. Status HTTP: {resp.status_code}"
            soup = BeautifulSoup(resp.text, "html.parser")
            for s in soup(["script", "style", "nav", "footer", "header"]):
                s.extract()
            text = soup.get_text(separator=" ", strip=True)
            return text[:4000] + ("\n...[Conteúdo truncado por limite de tamanho]" if len(text) > 4000 else "")
    except Exception as e:
        return f"Erro ao acessar e extrair conteúdo da URL: {e}"

def execute_python_code(code: str) -> str:
    """Executa dinamicamente um código Python em sandbox e retorna o output do console ou erros."""
    stdout_buffer = io.StringIO()
    stderr_buffer = io.StringIO()
    try:
        with contextlib.redirect_stdout(stdout_buffer), contextlib.redirect_stderr(stderr_buffer):
            exec_globals = {"__builtins__": __builtins__}
            exec(code, exec_globals)
        out = stdout_buffer.getvalue()
        err = stderr_buffer.getvalue()
        res = ""
        if out:
            res += f"OUTPUT:\n{out}\n"
        if err:
            res += f"ERROS:\n{err}\n"
        return res.strip() if res.strip() else "Código executado com sucesso (sem output)."
    except Exception as e:
        return f"Erro ao executar o código Python: {str(e)}"

def get_system_datetime() -> str:
    """Retorna a data e hora exata do sistema."""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

# --- SYSTEM PROMPT & COGNITIVE ARCHITECTURE ---
SYSTEM_PROMPT = """Você é o HERMES 3.0 ENTERPRISE CORE, um Agente Autônomo de Inteligência Artificial de alta precisão, capacidade técnica elevada e tom altamente resolutivo.

SUA CAIXA DE FERRAMENTAS:
1. 'web_search': Use para pesquisar fatos, tendências, notícias e dados em tempo real.
2. 'fetch_webpage': Use para abrir e ler artigos ou documentações técnicas completas a partir de uma URL.
3. 'execute_python_code': Use para realizar cálculos matemáticos avançados, processar strings, formatar dados ou validar lógica com Python.
4. 'get_system_datetime': Use para saber a data e hora atuais.

DIRETRIZES DE ATUAÇÃO:
- Se precisar de dados da web, pesquise. Se a busca retornar um link relevante, use 'fetch_webpage' para ler o conteúdo completo.
- Se o usuário pedir cálculos complexos ou análise lógica, use 'execute_python_code' para garantir precisão matemática de 100%.
- Formate suas respostas usando Markdown elegante com títulos, listas organizadas e blocos de código com a linguagem especificada.
- Seja direto, claro e forneça soluções prontas para produção.
"""

class ChatPayload(BaseModel):
    message: str

@app.get("/", response_class=HTMLResponse)
def read_root():
    return "<h3>Hermes Enterprise 3.0 está online! Acesse <a href='/chat' style='color:#38bdf8;'>/chat</a> para interagir.</h3>"

@app.get("/api/history")
def get_history():
    return JSONResponse(content={"status": "success", "history": get_history_for_ui()})

@app.delete("/api/history")
def clear_history():
    clear_db_history()
    return JSONResponse(content={"status": "success", "message": "Memória resetada."})

@app.post("/api/chat")
async def chat_endpoint(payload: ChatPayload):
    user_msg = payload.message.strip()
    if not user_msg:
        return JSONResponse(content={"status": "error", "reply": "Mensagem vazia."})

    if not client:
        return JSONResponse(content={
            "status": "error",
            "reply": "⚠️ GEMINI_API_KEY não foi configurada nas variáveis do Render."
        })

    save_message("user", user_msg)

    # Identificação dinâmica de modelos de alta capacidade
    candidate_models = []
    try:
        models_page = client.models.list()
        for m in models_page:
            name = m.name.replace("models/", "") if hasattr(m, "name") else str(m)
            if "gemini" in name.lower() and not any(x in name.lower() for x in ["embed", "imagen", "aqa", "tts", "stt"]):
                candidate_models.append(name)
    except Exception as e:
        print(f"Erro ao listar modelos: {e}")

    defaults = ["gemini-2.5-flash", "gemini-2.0-flash", "gemini-1.5-pro", "gemini-1.5-flash"]
    for d in defaults:
        if d not in candidate_models:
            candidate_models.append(d)

    history_contents = get_history_for_gemini(limit=16)

    config = types.GenerateContentConfig(
        system_instruction=SYSTEM_PROMPT,
        tools=[web_search, fetch_webpage, execute_python_code, get_system_datetime],
        temperature=0.4
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
        "reply": f"Erro na API do Gemini: {last_error}"
    })

@app.get("/chat", response_class=HTMLResponse)
async def get_chat_ui():
    html_content = """<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Hermes 3.0 Enterprise Core</title>
    <!-- Marked.js para suporte completo a Markdown -->
    <script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
    <!-- Highlight.js para sintaxe de código colorida -->
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/styles/atom-one-dark.min.css">
    <script src="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/highlight.min.js"></script>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; font-family: 'Inter', system-ui, -apple-system, sans-serif; }
        body { background-color: #0b0f19; color: #f1f5f9; display: flex; flex-direction: column; height: 100vh; justify-content: center; align-items: center; }
        .chat-container { width: 92%; max-width: 1050px; height: 90vh; background-color: #111827; border-radius: 16px; display: flex; flex-direction: column; box-shadow: 0 20px 50px rgba(0,0,0,0.6); border: 1px solid #1f2937; }
        .chat-header { padding: 20px 28px; background-color: #0b0f19; border-bottom: 1px solid #1f2937; border-top-left-radius: 16px; border-top-right-radius: 16px; display: flex; align-items: center; justify-content: space-between; }
        .chat-header h2 { color: #38bdf8; font-size: 1.3rem; font-weight: 700; display: flex; align-items: center; gap: 10px; }
        .header-actions { display: flex; gap: 12px; align-items: center; }
        .status-badge { background-color: rgba(16, 185, 129, 0.15); color: #10b981; border: 1px solid #059669; padding: 4px 10px; border-radius: 20px; font-size: 0.75rem; font-weight: 600; }
        .clear-btn { padding: 8px 16px; background-color: #ef4444; color: #fff; border: none; border-radius: 8px; font-size: 0.85rem; font-weight: 600; cursor: pointer; transition: all 0.2s; }
        .clear-btn:hover { background-color: #dc2626; transform: translateY(-1px); }
        .chat-box { flex: 1; padding: 24px; overflow-y: auto; display: flex; flex-direction: column; gap: 20px; }
        .message { padding: 16px 20px; border-radius: 12px; max-width: 88%; line-height: 1.6; font-size: 0.98rem; word-break: break-word; }
        .user-msg { background-color: #0284c7; color: #ffffff; align-self: flex-end; border-bottom-right-radius: 2px; }
        .bot-msg { background-color: #1f2937; color: #e5e7eb; align-self: flex-start; border-bottom-left-radius: 2px; border: 1px solid #374151; }
        .bot-msg code { background-color: #111827; padding: 2px 6px; border-radius: 4px; font-family: 'Fira Code', monospace; font-size: 0.9em; }
        .bot-msg pre { background-color: #0b0f19; padding: 14px; border-radius: 8px; overflow-x: auto; margin: 10px 0; border: 1px solid #374151; }
        .status-msg { background-color: rgba(56, 189, 248, 0.08); color: #38bdf8; border: 1px dashed #0284c7; align-self: flex-start; font-size: 0.88rem; font-style: italic; }
        .chat-input-area { padding: 18px 24px; background-color: #0b0f19; border-top: 1px solid #1f2937; display: flex; gap: 12px; border-bottom-left-radius: 16px; border-bottom-right-radius: 16px; }
        input[type="text"] { flex: 1; padding: 14px 18px; background-color: #1f2937; border: 1px solid #374151; border-radius: 10px; color: #fff; outline: none; font-size: 1rem; transition: border-color 0.2s; }
        input[type="text"]:focus { border-color: #38bdf8; }
        button.send-btn { padding: 14px 28px; background-color: #0284c7; border: none; border-radius: 10px; color: #fff; font-weight: 600; cursor: pointer; transition: all 0.2s; font-size: 1rem; }
        button.send-btn:hover { background-color: #0369a1; transform: translateY(-1px); }
        button:disabled { background-color: #374151; cursor: not-allowed; }
    </style>
</head>
<body>
    <div class="chat-container">
        <div class="chat-header">
            <h2>🤖 Hermes 3.0 Enterprise Core</h2>
            <div class="header-actions">
                <span class="status-badge">🟢 Web + Python + Memory Active</span>
                <button class="clear-btn" onclick="clearMemory()">🗑️ Resetar Memória</button>
            </div>
        </div>
        <div class="chat-box" id="chatBox">
            <div class="message bot-msg">Olá! Sou o **Hermes 3.0 Enterprise**. Possuo ambiente de execução Python integrado, suporte a consultas e leituras web em tempo real e memória persistente. Como posso ajudar?</div>
        </div>
        <div class="chat-input-area">
            <input type="text" id="userInput" placeholder="Digite seu comando, dúvida ou instrução técnica..." onkeydown="if(event.key==='Enter') sendMessage()">
            <button class="send-btn" id="sendBtn" onclick="sendMessage()">Enviar</button>
        </div>
    </div>

    <script>
        // Configura renderização de Markdown e Highlights
        marked.setOptions({
            highlight: function(code, lang) {
                if (lang && hljs.getLanguage(lang)) {
                    return hljs.highlight(code, { language: lang }).value;
                }
                return hljs.highlightAuto(code).value;
            },
            breaks: true
        });

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
                        if (msg.role === 'user') {
                            div.textContent = msg.content;
                        } else {
                            div.innerHTML = marked.parse(msg.content);
                        }
                        chatBox.appendChild(div);
                    });
                    chatBox.scrollTop = chatBox.scrollHeight;
                }
            } catch (err) {
                console.error("Erro ao carregar histórico:", err);
            }
        }

        async function clearMemory() {
            if (!confirm("Confirmar exclusão de todo o histórico de conversas?")) return;
            try {
                await fetch('/api/history', { method: 'DELETE' });
                const chatBox = document.getElementById('chatBox');
                chatBox.innerHTML = '<div class="message bot-msg">Memória zerada com sucesso. Como posso ajudar?</div>';
            } catch (err) {
                alert("Erro ao limpar banco de dados.");
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
            statusDiv.textContent = '⚡ [Hermes Enterprise Core] Executando análise, ferramentas e síntese...';
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
                botDiv.innerHTML = marked.parse(data.reply);
                chatBox.appendChild(botDiv);

            } catch (err) {
                statusDiv.remove();
                const errorDiv = document.createElement('div');
                errorDiv.className = 'message bot-msg';
                errorDiv.style.color = '#f87171';
                errorDiv.textContent = 'Erro ao se comunicar com o servidor.';
                chatBox.appendChild(errorDiv);
            } finally {
                input.disabled = false;
                sendBtn.disabled = false;
                input.focus();
                chatBox.scrollTop = chatBox.scrollHeight;
            }
        }

        window.onload = loadHistory;
    </script>
</body>
</html>"""
    return HTMLResponse(content=html_content)