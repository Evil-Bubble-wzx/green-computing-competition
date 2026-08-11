"""
联网搜索 Provider 抽象基类

用于补充数据库之外的最新政策、新闻、行业动态。
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Optional


@dataclass
class WebSearchResult:
    """单条搜索结果"""
    title: str
    url: str
    snippet: str
    source: str = ""           # 来源域名


class BaseWebSearch(ABC):
    """联网搜索 Provider 抽象基类"""

    @abstractmethod
    def search(
        self,
        query: str,
        max_results: int = 5,
        trusted_domains: Optional[list[str]] = None,
        trace: Optional[Any] = None,
    ) -> list[WebSearchResult]:
        """执行联网搜索

        Args:
            query: 搜索查询
            max_results: 最大返回数
            trusted_domains: 可信域名过滤 (优先排序，不丢弃非可信结果)
            trace: 可选 TraceContext

        Returns:
            list[WebSearchResult]: 搜索结果
        """
        ...
