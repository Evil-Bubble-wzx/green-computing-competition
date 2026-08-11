"""
Data Query MCP Server — 绿色算力数据查询服务

通过 MCP stdio transport 暴露 8 个数据查询工具。
协议消息走 stdout，日志走 stderr。

用法:
    python main.py mcp-data
    或在 Claude Desktop 配置中直接启动本文件
"""

from __future__ import annotations

import asyncio
import logging
import sys
from pathlib import Path

# 确保项目根目录可导入
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import mcp.server.stdio

from src.core.settings import load_settings
from src.data.database import DatabaseManager
from src.data.queries import QueryEngine
from src.mcp_servers.data_query.protocol_handler import create_data_query_server

SERVER_NAME = "green-computing-data-query"
SERVER_VERSION = "0.1.0"


def _setup_logging():
    """所有日志走 stderr（stdout 保留给 MCP JSON-RPC）"""
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    for h in root.handlers[:]:
        if isinstance(h, logging.StreamHandler) and not isinstance(h, logging.FileHandler):
            root.removeHandler(h)
    root.addHandler(logging.StreamHandler(sys.stderr))


async def run_async() -> int:
    _setup_logging()
    logger = logging.getLogger("mcp_data_query")
    logger.info("Starting Data Query MCP Server...")

    # 加载配置 + 数据库
    settings = load_settings("config/settings.yaml")
    db = DatabaseManager(settings)
    qe = QueryEngine(db)

    # 创建 MCP Server
    server = create_data_query_server(SERVER_NAME, SERVER_VERSION, db, qe)

    # 启动 stdio transport
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream, write_stream, server.create_initialization_options()
        )

    logger.info("Data Query MCP Server 停止")
    return 0


def main() -> int:
    return asyncio.run(run_async())


if __name__ == "__main__":
    sys.exit(main())
