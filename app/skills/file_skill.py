import os
from typing import Dict, Any

async def read_file_content(file_path: str) -> Dict[str, Any]:
    try:
        if not os.path.exists(file_path):
            return {"status": "error", "message": f"Arquivo '{file_path}' não encontrado."}
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
        return {"status": "success", "content": content}
    except Exception as e:
        return {"status": "error", "message": str(e)}

async def write_file_content(file_path: str, content: str) -> Dict[str, Any]:
    try:
        os.makedirs(os.path.dirname(os.path.abspath(file_path)), exist_ok=True)
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
        return {"status": "success", "message": f"Arquivo '{file_path}' salvo com sucesso."}
    except Exception as e:
        return {"status": "error", "message": str(e)}

async def list_directory_content(directory_path: str = ".") -> Dict[str, Any]:
    try:
        items = os.listdir(directory_path)
        return {"status": "success", "items": items}
    except Exception as e:
        return {"status": "error", "message": str(e)}
