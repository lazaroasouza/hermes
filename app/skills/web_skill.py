import asyncio
from typing import Dict, Any, List

try:
    from duckduckgo_search import DDGS
except ImportError:
    DDGS = None

def _sync_web_search(query: str, max_results: int = 5) -> List[Dict[str, str]]:
    if DDGS is None:
        return [{"error": "A biblioteca duckduckgo-search não está instalada."}]
    try:
        results = []
        with DDGS() as ddgs:
            for r in ddgs.text(query, max_results=max_results):
                results.append({
                    "title": r.get("title", ""),
                    "href": r.get("href", ""),
                    "snippet": r.get("body", "")
                })
        return results
    except Exception as e:
        return [{"error": f"Erro durante a busca na web: {str(e)}"}]

async def web_search(query: str, max_results: int = 5) -> Dict[str, Any]:
    try:
        res = await asyncio.to_thread(_sync_web_search, query, max_results)
        return {"status": "success", "query": query, "results": res}
    except Exception as e:
        return {"status": "error", "message": str(e)}
