"""
Review MCP Server — 企划书评审与报告生成

用法:
    python main.py mcp-review
"""

from __future__ import annotations

import asyncio, logging, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from openai import OpenAI
import mcp.server.stdio

from src.core.settings import load_settings
from src.data.database import DatabaseManager
from src.data.queries import QueryEngine
from src.libs.llm.llm_factory import LLMFactory
from src.retrieval.hybrid_search import HybridSearcher
from src.chat.engine import ChatEngine
from src.review.minimax_reviewer import MiniMaxReviewer
from src.mcp_servers.review.protocol_handler import create_review_server

SERVER_NAME = "green-computing-review"
SERVER_VERSION = "0.1.0"


def _setup_logging():
    root = logging.getLogger(); root.setLevel(logging.INFO)
    for h in root.handlers[:]:
        if isinstance(h, logging.StreamHandler) and not isinstance(h, logging.FileHandler):
            root.removeHandler(h)
    root.addHandler(logging.StreamHandler(sys.stderr))


async def run_async() -> int:
    _setup_logging()
    logger = logging.getLogger("mcp_review")
    logger.info("Starting Review MCP Server...")

    settings = load_settings("config/settings.yaml")

    # 初始化各组件
    db = DatabaseManager(settings)
    qe = QueryEngine(db)
    llm = LLMFactory.create(settings)
    searcher = HybridSearcher(query_engine=qe)
    chat_engine = ChatEngine(llm, searcher)

    # MiniMax Reviewer — 通过 OpenAI 兼容接口
    minimax_client = OpenAI(
        api_key=settings.minimax.api_key,
        base_url=settings.minimax.base_url,
    )

    reviewer = MiniMaxReviewer()

    def call_minimax(prompt: str) -> str:
        resp = minimax_client.chat.completions.create(
            model=settings.minimax.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,
        )
        return resp.choices[0].message.content or ""

    reviewer.set_minimax_fn(call_minimax)

    server = create_review_server(SERVER_NAME, SERVER_VERSION,
        chat_engine=chat_engine, reviewer=reviewer, settings=settings)

    async with mcp.server.stdio.stdio_server() as (rd, wr):
        await server.run(rd, wr, server.create_initialization_options())

    logger.info("Review MCP Server 停止")
    return 0


def main() -> int:
    return asyncio.run(run_async())


if __name__ == "__main__":
    sys.exit(main())
