import os
from typing import Dict, Any, List

async def scan_project_directory(directory_path: str = ".", max_files: int = 50) -> Dict[str, Any]:
    """Escaneia um diretório e retorna a estrutura da árvore e lista de arquivos de código."""
    if not os.path.exists(directory_path):
        return {"status": "error", "message": f"Diretório '{directory_path}' não encontrado."}

    file_tree = []
    ignore_dirs = {".git", ".venv", "__pycache__", "node_modules", ".idea", ".vscode"}

    for root, dirs, files in os.walk(directory_path):
        dirs[:] = [d for d in dirs if d not in ignore_dirs]
        for file in files:
            rel_path = os.path.relpath(os.path.join(root, file), directory_path)
            file_tree.append(rel_path)
            if len(file_tree) >= max_files:
                break
        if len(file_tree) >= max_files:
            break

    return {
        "status": "success",
        "total_files": len(file_tree),
        "files": file_tree
    }

async def read_multiple_files(file_paths: List[str]) -> Dict[str, Any]:
    """Lê o conteúdo de múltiplos arquivos do projeto para análise de contexto."""
    contents = {}
    for path in file_paths:
        if os.path.exists(path) and os.path.isfile(path):
            try:
                with open(path, "r", encoding="utf-8", errors="ignore") as f:
                    contents[path] = f.read()
            except Exception as e:
                contents[path] = f"Erro ao ler arquivo: {str(e)}"
        else:
            contents[path] = "Arquivo não encontrado."

    return {"status": "success", "files": contents}
