"""
摄入管线编排

PDF → 解析 → 分块 → 向量化 → ChromaDB
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from src.ingestion.pdf_parser import PDFParser, ParsedDocument
from src.ingestion.chunker import DocumentChunker, Chunk
from src.ingestion.vector_store import ChromaVectorStore


@dataclass
class IngestionResult:
    file_name: str
    status: str            # "success" | "failed"
    chunks_count: int = 0
    pages: int = 0
    error: str = ""


class IngestionPipeline:
    """PDF 摄入管线

    用法:
        pipeline = IngestionPipeline(embedding_provider, vector_store, chunk_size=800)
        result = pipeline.ingest("/path/to/proposal.pdf")
    """

    def __init__(self, embedding_provider, vector_store: ChromaVectorStore, chunk_size: int = 800, chunk_overlap: int = 150):
        self.embedding = embedding_provider
        self.store = vector_store
        self.parser = PDFParser()
        self.chunker = DocumentChunker(chunk_size, chunk_overlap)

    def ingest(self, file_path: str | Path) -> IngestionResult:
        """摄入单个文档"""
        path = Path(file_path)
        try:
            # 1. 解析
            doc = self.parser.parse(path)

            # 2. 分块
            chunks = self.chunker.split(doc)
            if not chunks:
                return IngestionResult(file_name=path.name, status="success", chunks_count=0, pages=doc.total_pages)

            # 3. 向量化
            texts = [c.text for c in chunks]
            embeddings = self.embedding.embed(texts)

            # 4. 入库
            ids = [f"{path.stem}_{c.index}_{uuid.uuid4().hex[:6]}" for c in chunks]
            metadatas = [{"source": path.name, "page": c.metadata.get("page", 0)} for c in chunks]
            self.store.add_chunks(ids, texts, embeddings, metadatas)

            return IngestionResult(
                file_name=path.name,
                status="success",
                chunks_count=len(chunks),
                pages=doc.total_pages,
            )
        except Exception as e:
            return IngestionResult(file_name=path.name, status="failed", error=str(e))

    def list_documents(self) -> list[str]:
        return self.store.list_sources()

    def delete_document(self, file_name: str) -> int:
        return self.store.delete_by_source(file_name)

    def count(self) -> int:
        return self.store.count()
