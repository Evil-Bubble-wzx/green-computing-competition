"""
Search MCP Server — 混合检索服务

用法:
    python main.py mcp-search
"""

from __future__ import annotations

import asyncio, logging, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import mcp.server.stdio

from src.core.settings import load_settings
from src.data.database import DatabaseManager
from src.data.queries import QueryEngine
from src.retrieval.hybrid_search import HybridSearcher
from src.mcp_servers.search.protocol_handler import create_search_server

SERVER_NAME = "green-computing-search"
SERVER_VERSION = "0.1.0"


def _setup_logging():
    root = logging.getLogger(); root.setLevel(logging.INFO)
    for h in root.handlers[:]:
        if isinstance(h, logging.StreamHandler) and not isinstance(h, logging.FileHandler):
            root.removeHandler(h)
    root.addHandler(logging.StreamHandler(sys.stderr))


async def run_async() -> int:
    _setup_logging()
    logger = logging.getLogger("mcp_search")
    logger.info("Starting Search MCP Server...")

    settings = load_settings("config/settings.yaml")
    db = DatabaseManager(settings)
    qe = QueryEngine(db)

    # Web search
    web = None
    if settings.web_search.enabled:
        from src.libs.search.builtin_web_search import BuiltinWebSearch
        web = BuiltinWebSearch(settings)

    searcher = HybridSearcher(query_engine=qe, web_search=web)

    server = create_search_server(SERVER_NAME, SERVER_VERSION, searcher)
    async with mcp.server.stdio.stdio_server() as (rd, wr):
        await server.run(rd, wr, server.create_initialization_options())

    logger.info("Search MCP Server 停止")
    return 0


def main() -> int:
    return asyncio.run(run_async())


if __name__ == "__main__":
    sys.exit(main())
