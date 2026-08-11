"""
文档分块器

使用 langchain RecursiveCharacterTextSplitter 做中文语义分块。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional
from pathlib import Path


@dataclass
class Chunk:
    text: str
    index: int
    source_file: str
    page_range: str = ""
    metadata: dict = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class DocumentChunker:
    """文档分块器

    用法:
        chunker = DocumentChunker(chunk_size=800, chunk_overlap=150)
        chunks = chunker.split(parsed_doc)
    """

    def __init__(self, chunk_size: int = 800, chunk_overlap: int = 150):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def split(self, parsed_doc, source_file: str | None = None) -> list[Chunk]:
        from langchain_text_splitters import RecursiveCharacterTextSplitter

        source = source_file or parsed_doc.file_name

        splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
            separators=["\n\n", "\n", "。", "；", "，", " ", ""],
            length_function=len,
        )

        # 逐页分块，保留页码信息
        chunks = []
        index = 0
        for page in parsed_doc.pages:
            if not page.text.strip():
                continue
            page_chunks = splitter.split_text(page.text)
            for pc in page_chunks:
                chunks.append(Chunk(
                    text=pc,
                    index=index,
                    source_file=source,
                    page_range=str(page.page_number),
                    metadata={
                        "source": source,
                        "page": page.page_number,
                    },
                ))
                index += 1

        return chunks
