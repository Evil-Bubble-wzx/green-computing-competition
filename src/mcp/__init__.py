"""
MCP Server - Model Context Protocol 工具暴露

通过 MCP 协议暴露绿色算力数据查询工具，
支持 Claude Desktop、GitHub Copilot 等 AI 客户端直接调用。

暴露的工具:
  - query_province_score: 查询省份综合得分
  - query_layout_type:   查询布局类型
  - query_dimension:     查询七维得分
  - list_provinces:      列出所有省份
  - compare_provinces:   多省份对比
  - search_knowledge:    检索知识库
"""
