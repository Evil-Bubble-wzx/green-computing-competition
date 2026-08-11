"""
Ingestion MCP 工具集
"""

import asyncio
import json


def register_all(handler, pipeline):
    if pipeline is None:
        return

    # ------------------------------------------------------------------
    # 1. ingest_document
    # ------------------------------------------------------------------
    async def ingest_document(file_path: str):
        """摄入 PDF 文档到知识库"""
        result = await asyncio.to_thread(pipeline.ingest, file_path)
        return json.dumps({
            "file_name": result.file_name,
            "status": result.status,
            "chunks_created": result.chunks_count,
            "pages": result.pages,
            "error": result.error if result.status == "failed" else None,
        }, ensure_ascii=False)

    handler.register_tool(
        "ingest_document",
        "摄入 PDF 企划书文档：解析文本 → 分块 → 向量化 → 存入 ChromaDB 知识库",
        {
            "type": "object",
            "properties": {
                "file_path": {"type": "string", "description": "PDF 文件的绝对路径"},
            },
            "required": ["file_path"],
        },
        ingest_document,
    )

    # ------------------------------------------------------------------
    # 2. list_documents
    # ------------------------------------------------------------------
    async def list_documents():
        """列出已摄入的文档"""
        docs = pipeline.list_documents()
        total = pipeline.count()
        return json.dumps({"total_chunks": total, "documents": docs}, ensure_ascii=False)

    handler.register_tool(
        "list_documents",
        "列出所有已摄入的企划书文档",
        {"type": "object", "properties": {}, "required": []},
        list_documents,
    )

    # ------------------------------------------------------------------
    # 3. delete_document
    # ------------------------------------------------------------------
    async def delete_document(file_name: str):
        """删除已摄入的文档"""
        removed = await asyncio.to_thread(pipeline.delete_document, file_name)
        return json.dumps({"file_name": file_name, "chunks_removed": removed}, ensure_ascii=False)

    handler.register_tool(
        "delete_document",
        "删除指定文档的所有向量数据",
        {
            "type": "object",
            "properties": {
                "file_name": {"type": "string", "description": "文档文件名（如 proposal.pdf）"},
            },
            "required": ["file_name"],
        },
        delete_document,
    )
