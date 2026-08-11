"""
MCP 工具定义 (骨架)

计划暴露的工具:
  1. query_province_score  - 查询省份综合得分
  2. query_layout_type     - 查询布局类型
  3. query_dimension       - 查询七维得分
  4. list_provinces        - 列出所有省份
  5. compare_provinces     - 多省份对比
  6. search_knowledge      - 检索知识库 (企划书)
  7. get_trend             - 获取趋势数据
  8. get_lisa_map          - 获取 LISA 空间数据
"""

TOOL_DEFINITIONS = [
    {
        "name": "query_province_score",
        "description": "查询指定省份的综合得分、排名和布局类型",
        "inputSchema": {
            "type": "object",
            "properties": {
                "province": {
                    "type": "string",
                    "description": "省份标准名称，如 '江苏'、'广东'",
                },
                "year": {
                    "type": "integer",
                    "description": "年份 (2016-2024)，默认 2024",
                    "default": 2024,
                },
            },
            "required": ["province"],
        },
    },
    {
        "name": "query_layout_type",
        "description": "查询指定布局类型包含的所有省份",
        "inputSchema": {
            "type": "object",
            "properties": {
                "layout_type": {
                    "type": "string",
                    "description": "布局类型: 高适宜综合承载区 / 需求网络驱动区 / 能源低碳优势承接区 / 综合潜力提升区 / 约束控制区",
                },
            },
            "required": ["layout_type"],
        },
    },
    {
        "name": "compare_provinces",
        "description": "比较多个省份的综合得分、七维得分",
        "inputSchema": {
            "type": "object",
            "properties": {
                "provinces": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "需要对比的省份列表",
                },
                "year": {
                    "type": "integer",
                    "description": "年份 (2016-2024)，默认 2024",
                },
            },
            "required": ["provinces"],
        },
    },
    {
        "name": "search_knowledge",
        "description": "在企划书知识库中检索相关内容",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "检索查询",
                },
                "top_k": {
                    "type": "integer",
                    "description": "返回结果数，默认 5",
                },
            },
            "required": ["query"],
        },
    },
]
