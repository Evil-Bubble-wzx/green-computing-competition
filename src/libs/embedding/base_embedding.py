"""
Embedding Provider 抽象基类

定义文本向量化的统一接口。
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Optional


class BaseEmbedding(ABC):
    """Embedding Provider 抽象基类

    所有 Embedding 实现需提供:
    - embed():      批量文本 → 向量列表
    - embed_query(): 单条查询 → 向量
    - dimensions:    向量维度
    """

    @abstractmethod
    def embed(self, texts: list[str], trace: Optional[Any] = None) -> list[list[float]]:
        """批量文本向量化

        Args:
            texts: 文本列表
            trace: 可选 TraceContext

        Returns:
            list[list[float]]: 每条文本对应的向量
        """
        ...

    @abstractmethod
    def embed_query(self, query: str) -> list[float]:
        """单条查询向量化 (用于检索)

        Args:
            query: 查询文本

        Returns:
            list[float]: 向量
        """
        ...

    @property
    @abstractmethod
    def dimensions(self) -> int:
        """向量维度"""
        ...
