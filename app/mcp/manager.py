import os
from typing import Dict, Any
from dotenv import load_dotenv

load_dotenv()

class MCPManager:
    def __init__(self):
        self.postgres_url = os.getenv("POSTGRES_URL", "postgresql://postgres:postgres@localhost:5432/hermes_db")
        self.servers = {
            "filesystem": {"command": "npx", "args": ["-y", "@modelcontextprotocol/server-filesystem", "C:\\Projetos\\hermes"]},
            "postgres": {"command": "npx", "args": ["-y", "@modelcontextprotocol/server-postgres", self.postgres_url]}
        }

    async def get_status(self) -> Dict[str, Any]:
        return {
            "active_servers": list(self.servers.keys()),
            "status": "ready"
        }

mcp_hub = MCPManager()
