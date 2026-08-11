"""
Ingestion MCP Protocol Handler
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import Any, Callable

from mcp import types
from mcp.server.lowlevel import Server

logger = logging.getLogger("mcp_ingestion")


@dataclass
class ToolDefinition:
    name: str
    description: str
    input_schema: dict[str, Any]
    handler: Callable[..., Any]


@dataclass
class ProtocolHandler:
    server_name: str
    server_version: str
    tools: dict[str, ToolDefinition] = field(default_factory=dict)

    def register_tool(self, name, description, input_schema, handler):
        if name in self.tools:
            raise ValueError(f"Tool '{name}' 已注册")
        self.tools[name] = ToolDefinition(name, description, input_schema, handler)

    def get_tool_schemas(self) -> list[types.Tool]:
        return [
            types.Tool(name=t.name, description=t.description, inputSchema=t.input_schema)
            for t in self.tools.values()
        ]

    async def execute_tool(self, name: str, arguments: dict[str, Any]) -> types.CallToolResult:
        tool = self.tools.get(name)
        if not tool:
            return types.CallToolResult(
                content=[types.TextContent(type="text", text=f"Error: 未知工具 '{name}'")],
                isError=True,
            )
        try:
            result = await tool.handler(**arguments)
            if isinstance(result, types.CallToolResult):
                return result
            if isinstance(result, str):
                return types.CallToolResult(content=[types.TextContent(type="text", text=result)], isError=False)
            return types.CallToolResult(
                content=[types.TextContent(type="text", text=json.dumps(result, ensure_ascii=False, indent=2))],
                isError=False,
            )
        except Exception as e:
            logger.exception("Tool '%s' 执行失败", name)
            return types.CallToolResult(
                content=[types.TextContent(type="text", text=f"Error: {e}")],
                isError=True,
            )


def create_ingestion_server(name, version, pipeline=None):
    handler = ProtocolHandler(name, version)

    from src.mcp_servers.ingestion.tools import register_all
    register_all(handler, pipeline)

    async def on_list_tools(ctx, params):
        return handler.get_tool_schemas()

    async def on_call_tool(ctx, params):
        return await handler.execute_tool(params.name, params.arguments or {})

    server = Server(name, version=version, on_list_tools=on_list_tools, on_call_tool=on_call_tool)
    server._protocol_handler = handler
    return server
