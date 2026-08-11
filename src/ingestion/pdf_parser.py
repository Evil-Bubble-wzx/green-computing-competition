"""
PDF 文档解析器

使用 pdfplumber 提取文本和表格。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class ParsedPage:
    page_number: int
    text: str
    tables: list[list[list[str]]] = field(default_factory=list)


@dataclass
class ParsedDocument:
    file_name: str
    file_path: str
    total_pages: int
    pages: list[ParsedPage]
    full_text: str = ""


class PDFParser:
    """PDF 文档解析器

    用法:
        parser = PDFParser()
        doc = parser.parse("/path/to/proposal.pdf")
        print(doc.full_text)
    """

    def parse(self, file_path: str | Path) -> ParsedDocument:
        import pdfplumber

        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"文件不存在: {file_path}")
        if path.suffix.lower() != ".pdf":
            raise ValueError(f"不支持的文件格式: {path.suffix}（目前仅支持 .pdf）")

        pages = []
        full_text_parts = []

        with pdfplumber.open(str(path)) as pdf:
            for i, page in enumerate(pdf.pages):
                text = page.extract_text() or ""
                tables = page.extract_tables() or []

                pages.append(ParsedPage(
                    page_number=i + 1,
                    text=text,
                    tables=tables,
                ))
                full_text_parts.append(text)

                # 表格也拼进全文
                for table in tables:
                    for row in table:
                        row_text = " | ".join(str(c) if c else "" for c in row)
                        full_text_parts.append(row_text)

        return ParsedDocument(
            file_name=path.name,
            file_path=str(path.absolute()),
            total_pages=len(pages),
            pages=pages,
            full_text="\n\n".join(full_text_parts),
        )
