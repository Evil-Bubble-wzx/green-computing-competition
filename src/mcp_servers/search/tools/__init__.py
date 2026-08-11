"""
Search MCP 工具集
"""

import asyncio, json


def register_all(handler, searcher):
    if searcher is None:
        return

    async def search(query: str, top_k: int = 8):
        """混合检索"""
        result = await asyncio.to_thread(searcher.search, query, top_k)
        return json.dumps({
            "query": result.query,
            "total_hits": result.fusion_count,
            "channels": {"database": result.db_count, "vector": result.vector_count, "web": result.web_count},
            "hits": [
                {"source": h.source, "title": h.title, "content": h.content[:500], "score": round(h.score, 4), "url": h.url}
                for h in result.hits
            ],
        }, ensure_ascii=False)

    handler.register_tool("search", "混合检索：同时查询数据库、企划书知识库和联网资源，返回融合排序结果",
        {"type": "object", "properties": {
            "query": {"type": "string", "description": "搜索查询"},
            "top_k": {"type": "integer", "description": "返回结果数，默认8"},
        }, "required": ["query"]}, search)

    async def search_db(query: str, top_k: int = 5):
        """仅数据库检索"""
        result = await asyncio.to_thread(searcher.search, query, top_k, vec_k=0, web_k=0)
        return json.dumps({
            "hits": [{"title": h.title, "content": h.content[:400], "score": round(h.score, 4)}
                     for h in result.hits],
        }, ensure_ascii=False)

    handler.register_tool("search_db", "仅查询 PostgreSQL 中的绿色算力结构化数据",
        {"type": "object", "properties": {
            "query": {"type": "string", "description": "搜索查询"},
            "top_k": {"type": "integer", "description": "返回结果数，默认5"},
        }, "required": ["query"]}, search_db)

    async def search_web(query: str, top_k: int = 5):
        """仅联网搜索"""
        result = await asyncio.to_thread(searcher.search, query, top_k, db_k=0, vec_k=0)
        return json.dumps({
            "hits": [{"title": h.title, "content": h.content[:400], "url": h.url}
                     for h in result.hits],
        }, ensure_ascii=False)

    handler.register_tool("search_web", "仅联网搜索外部政策、新闻",
        {"type": "object", "properties": {
            "query": {"type": "string", "description": "搜索查询"},
            "top_k": {"type": "integer", "description": "返回结果数，默认5"},
        }, "required": ["query"]}, search_web)
