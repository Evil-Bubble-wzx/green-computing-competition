"""
MCP Server 主入口 (骨架)

完整 MCP 协议实现将在 Phase F 完成。
"""


class MCPServer:
    """
    MCP Server (骨架)。

    实现 MCP 协议，对外暴露绿色算力数据查询工具。
    """

    def __init__(self, settings, query_engine):
        self.settings = settings
        self.query_engine = query_engine

    def run(self):
        """启动 MCP Server (stdio transport)"""
        # TODO: Phase F - MCP Server 实现
        print("MCP Server starting...")
        print(f"Server: {self.settings.mcp.server_name} v{self.settings.mcp.server_version}")
        print("MCP Server not yet implemented (Phase F)")
