import json
import os
from typing import Dict, Any, List
from dotenv import load_dotenv
from openai import AsyncOpenAI

from app.skills.terminal_skill import run_powershell_command
from app.skills.file_skill import read_file_content, write_file_content, list_directory_content
from app.skills.web_skill import web_search
from app.skills.project_skill import scan_project_directory, read_multiple_files
from app.core.db import save_message, get_history
from app.core.agents import get_agent_prompt

load_dotenv()

TOOLS_SCHEMA = [
    {
        "type": "function",
        "function": {
            "name": "run_powershell_command",
            "description": "Executa comandos no terminal PowerShell local no Windows.",
            "parameters": {
                "type": "object",
                "properties": {"command": {"type": "string", "description": "Comando PowerShell"}},
                "required": ["command"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "read_file_content",
            "description": "Lê o conteúdo de um arquivo no disco.",
            "parameters": {
                "type": "object",
                "properties": {"file_path": {"type": "string", "description": "Caminho do arquivo"}},
                "required": ["file_path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "write_file_content",
            "description": "Cria ou substitui um arquivo no disco.",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {"type": "string", "description": "Caminho do arquivo"},
                    "content": {"type": "string", "description": "Conteúdo textual"}
                },
                "required": ["file_path", "content"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_directory_content",
            "description": "Lista itens de um diretório.",
            "parameters": {
                "type": "object",
                "properties": {"directory_path": {"type": "string", "description": "Caminho da pasta"}},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": "Realiza pesquisas na web em tempo real para obter dados e notícias recentes.",
            "parameters": {
                "type": "object",
                "properties": {"query": {"type": "string", "description": "Termo de pesquisa"}},
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "scan_project_directory",
            "description": "Escaneia a árvore de arquivos de um projeto inteiro.",
            "parameters": {
                "type": "object",
                "properties": {"directory_path": {"type": "string", "description": "Caminho do projeto"}},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "read_multiple_files",
            "description": "Lê múltiplos arquivos de um projeto de uma só vez.",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_paths": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Lista de caminhos de arquivos"
                    }
                },
                "required": ["file_paths"]
            }
        }
    }
]

class FallbackLLMEngine:
    def __init__(self):
        self.provider_chain = [
            {"name": "Google Gemini", "base_url": "https://generativelanguage.googleapis.com/v1beta/openai/", "api_key": os.getenv("GEMINI_API_KEY"), "model": os.getenv("GEMINI_MODEL", "gemini-2.5-flash")},
            {"name": "Groq", "base_url": "https://api.groq.com/openai/v1", "api_key": os.getenv("GROQ_API_KEY"), "model": os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")},
            {"name": "OpenRouter Free", "base_url": "https://openrouter.ai/api/v1", "api_key": os.getenv("OPENROUTER_API_KEY"), "model": os.getenv("OPENROUTER_MODEL", "openrouter/free")},
            {"name": "Cerebras AI", "base_url": "https://api.cerebras.ai/v1", "api_key": os.getenv("CEREBRAS_API_KEY"), "model": os.getenv("CEREBRAS_MODEL", "llama3.1-70b")},
            {"name": "SambaNova", "base_url": "https://api.sambanova.ai/v1", "api_key": os.getenv("SAMBANOVA_API_KEY"), "model": os.getenv("SAMBANOVA_MODEL", "Meta-Llama-3.3-70B-Instruct")},
            {"name": "DeepSeek", "base_url": "https://api.deepseek.com/v1", "api_key": os.getenv("DEEPSEEK_API_KEY"), "model": os.getenv("DEEPSEEK_MODEL", "deepseek-chat")},
            {"name": "OpenAI", "base_url": "https://api.openai.com/v1", "api_key": os.getenv("OPENAI_API_KEY"), "model": os.getenv("OPENAI_MODEL", "gpt-4o-mini")},
            {"name": "Ollama Local", "base_url": os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1"), "api_key": "ollama", "model": os.getenv("OLLAMA_MODEL", "qwen2.5:latest")}
        ]

    def _get_active_providers(self):
        active = []
        for p in self.provider_chain:
            if p["api_key"] or "localhost" in p["base_url"] or "127.0.0.1" in p["base_url"]:
                active.append({
                    "name": p["name"],
                    "client": AsyncOpenAI(api_key=p["api_key"] or "ollama", base_url=p["base_url"]),
                    "model": p["model"]
                })
        return active

    async def _completion_with_fallback(self, messages: List[Dict], tools=None):
        providers = self._get_active_providers()
        last_error = None

        for p in providers:
            try:
                kwargs = {"model": p["model"], "messages": messages}
                if tools:
                    kwargs["tools"] = tools
                    kwargs["tool_choice"] = "auto"
                response = await p["client"].chat.completions.create(**kwargs)
                return response, p["name"]
            except Exception as e:
                print(f"[CASCATA HERMES] Provedor '{p['name']}' indisponível: {e}. Transicionando...")
                last_error = e
                continue

        raise RuntimeError(f"Todos os provedores da cascata falharam. Último erro: {last_error}")

    async def _execute_tool(self, fn_name: str, args: Dict) -> Any:
        if fn_name == "run_powershell_command":
            return await run_powershell_command(args.get("command"))
        elif fn_name == "read_file_content":
            return await read_file_content(args.get("file_path"))
        elif fn_name == "write_file_content":
            return await write_file_content(args.get("file_path"), args.get("content"))
        elif fn_name == "list_directory_content":
            return await list_directory_content(args.get("directory_path", "."))
        elif fn_name == "web_search":
            return await web_search(args.get("query"))
        elif fn_name == "scan_project_directory":
            return await scan_project_directory(args.get("directory_path", "."))
        elif fn_name == "read_multiple_files":
            return await read_multiple_files(args.get("file_paths", []))
        else:
            return {"error": f"Ferramenta '{fn_name}' não suportada."}

    async def process_chat(self, user_input: str, session_id: str = "default-session", active_role: str = "architect") -> Dict[str, Any]:
        db_history = get_history(session_id, limit=10)

        system_instruction = (
            f"{get_agent_prompt(active_role)}\n"
            "Você possui um sistema AUTÔNOMO de Self-Healing (Autocorreção): se uma comando ou script falhar, "
            "analise a causa do erro no stderr/stdout, corrija os arquivos ou dependências e re-execute automaticamente até obter sucesso!"
        )

        messages = [
            {"role": "system", "content": system_instruction}
        ] + db_history + [{"role": "user", "content": user_input}]

        max_loops = 5
        loop_count = 0
        current_provider = "Google Gemini"

        while loop_count < max_loops:
            loop_count += 1
            response, current_provider = await self._completion_with_fallback(messages, tools=TOOLS_SCHEMA)
            message = response.choices[0].message

            if not message.tool_calls:
                final_text = message.content or "Tarefa executada."
                save_message(session_id, "user", user_input)
                save_message(session_id, "assistant", final_text)
                return {
                    "response": final_text,
                    "provider_used": current_provider,
                    "role_active": active_role,
                    "execution_trace": messages
                }

            messages.append(message)

            for tool_call in message.tool_calls:
                fn_name = tool_call.function.name
                args = json.loads(tool_call.function.arguments)

                tool_result = await self._execute_tool(fn_name, args)

                # --- SELF-HEALING DETECTOR ---
                if fn_name == "run_powershell_command" and isinstance(tool_result, dict):
                    returncode = tool_result.get("returncode", 0)
                    stderr = tool_result.get("stderr", "")
                    if returncode != 0 or stderr.strip():
                        tool_result["self_healing_alert"] = (
                            "ATENÇÃO (SELF-HEALING): A execução retornou erro! "
                            "Analise a mensagem de erro acima, ajuste o código ou instale a dependência necessária e tente novamente."
                        )

                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "name": fn_name,
                    "content": json.dumps(tool_result, ensure_ascii=False)
                })

        final_response, final_provider = await self._completion_with_fallback(messages)
        agent_text = final_response.choices[0].message.content or "Processamento concluído."

        save_message(session_id, "user", user_input)
        save_message(session_id, "assistant", agent_text)

        return {
            "response": agent_text,
            "provider_used": final_provider,
            "role_active": active_role,
            "execution_trace": messages
        }

llm_engine = FallbackLLMEngine()
