"""
Search MCP Protocol Handler
"""

from __future__ import annotations

import json, logging
from dataclasses import dataclass, field
from typing import Any

from mcp import types
from mcp.server.lowlevel import Server

logger = logging.getLogger("mcp_search")


@dataclass
class ToolDefinition:
    name: str; description: str; input_schema: dict[str, Any]; handler: Any


@dataclass
class ProtocolHandler:
    server_name: str; server_version: str
    tools: dict[str, ToolDefinition] = field(default_factory=dict)

    def register_tool(self, n, d, s, h):
        if n in self.tools: raise ValueError(f"'{n}' 已注册")
        self.tools[n] = ToolDefinition(n, d, s, h)

    def get_tool_schemas(self) -> list[types.Tool]:
        return [types.Tool(name=t.name, description=t.description, inputSchema=t.input_schema)
                for t in self.tools.values()]

    async def execute_tool(self, name, arguments):
        t = self.tools.get(name)
        if not t:
            return types.CallToolResult(content=[types.TextContent(type="text", text=f"未知工具: {name}")], isError=True)
        try:
            r = await t.handler(**arguments)
            if isinstance(r, types.CallToolResult): return r
            if isinstance(r, str): return types.CallToolResult(content=[types.TextContent(type="text", text=r)], isError=False)
            return types.CallToolResult(content=[types.TextContent(type="text",
                text=json.dumps(r, ensure_ascii=False, indent=2))], isError=False)
        except Exception as e:
            logger.exception("Tool '%s' 失败", name)
            return types.CallToolResult(content=[types.TextContent(type="text", text=f"Error: {e}")], isError=True)


def create_search_server(name, version, searcher=None):
    handler = ProtocolHandler(name, version)
    from src.mcp_servers.search.tools import register_all
    register_all(handler, searcher)

    async def on_list_tools(ctx, params): return handler.get_tool_schemas()
    async def on_call_tool(ctx, params): return await handler.execute_tool(params.name, params.arguments or {})

    server = Server(name, version=version, on_list_tools=on_list_tools, on_call_tool=on_call_tool)
    server._protocol_handler = handler
    return server
