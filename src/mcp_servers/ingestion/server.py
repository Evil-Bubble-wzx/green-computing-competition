"""
Ingestion MCP Server — PDF 企划书摄入服务

用法:
    python main.py mcp-ingest
"""

from __future__ import annotations

import asyncio
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import mcp.server.stdio

from src.core.settings import load_settings
from src.libs.embedding.qwen_embedding import QwenEmbedding
from src.ingestion.vector_store import ChromaVectorStore
from src.ingestion.pipeline import IngestionPipeline
from src.mcp_servers.ingestion.protocol_handler import create_ingestion_server

SERVER_NAME = "green-computing-ingestion"
SERVER_VERSION = "0.1.0"


def _setup_logging():
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    for h in root.handlers[:]:
        if isinstance(h, logging.StreamHandler) and not isinstance(h, logging.FileHandler):
            root.removeHandler(h)
    root.addHandler(logging.StreamHandler(sys.stderr))


async def run_async() -> int:
    _setup_logging()
    logger = logging.getLogger("mcp_ingestion")
    logger.info("Starting Ingestion MCP Server...")

    settings = load_settings("config/settings.yaml")

    # 构建摄入管线
    embedding = QwenEmbedding(settings)
    store = ChromaVectorStore(
        persist_dir=settings.vector_store.persist_directory,
        collection_name=settings.vector_store.collection_name,
    )
    pipeline = IngestionPipeline(
        embedding_provider=embedding,
        vector_store=store,
        chunk_size=settings.ingestion.chunk_size,
        chunk_overlap=settings.ingestion.chunk_overlap,
    )

    server = create_ingestion_server(SERVER_NAME, SERVER_VERSION, pipeline)

    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())

    logger.info("Ingestion MCP Server 停止")
    return 0


def main() -> int:
    return asyncio.run(run_async())


if __name__ == "__main__":
    sys.exit(main())
