import asyncio
import os
import subprocess
from typing import Dict, Any

def _decode_output(raw_bytes: bytes) -> str:
    if not raw_bytes:
        return ""
    for encoding in ["utf-8", "cp850", "cp1252", "latin1"]:
        try:
            return raw_bytes.decode(encoding)
        except UnicodeDecodeError:
            continue
    return raw_bytes.decode("utf-8", errors="replace")

def _sync_run_powershell(command: str, target_dir: str) -> Dict[str, Any]:
    result = subprocess.run(
        ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", command],
        cwd=target_dir,
        capture_output=True
    )
    return {
        "exit_code": result.returncode,
        "stdout": _decode_output(result.stdout),
        "stderr": _decode_output(result.stderr)
    }

async def run_powershell_command(command: str, working_dir: str = "C:\\Projetos\\hermes") -> Dict[str, Any]:
    target_dir = working_dir if os.path.exists(working_dir) else os.getcwd()
    try:
        return await asyncio.to_thread(_sync_run_powershell, command, target_dir)
    except Exception as exc:
        return {
            "exit_code": -1,
            "stdout": "",
            "stderr": f"Erro de execução: {type(exc).__name__} - {repr(exc)}"
        }
