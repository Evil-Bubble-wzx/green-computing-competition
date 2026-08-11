"""
Reranker Provider 抽象基类

检索后重排序：对粗排结果进行精排，提升 Top-K 质量。
支持两种策略: Cross-Encoder 模型重排 / LLM 推理重排
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Optional


@dataclass
class RankedDocument:
    """排序后的文档"""
    content: str
    score: float                        # 相关性分数 (0-1)
    index: int                          # 原始排名
    metadata: dict[str, Any] | None = None


class BaseReranker(ABC):
    """Reranker Provider 抽象基类"""

    @abstractmethod
    def rerank(
        self,
        query: str,
        documents: list[str],
        top_k: int = 5,
        **kwargs: Any,
    ) -> list[RankedDocument]:
        """对检索结果重排序

        Args:
            query: 用户查询
            documents: 粗排文档列表
            top_k: 返回前 K 条
            **kwargs: provider 特定参数

        Returns:
            list[RankedDocument]: 按相关性降序排列
        """
        ...
