"""
内置联网搜索 Provider

基于 Claude Code 提供的 WebSearch / WebFetch 工具。
在生产环境中可以替换为 SerpAPI、Bing API 等。
"""

from __future__ import annotations

from typing import Any, Optional

from src.libs.search.base_web_search import BaseWebSearch, WebSearchResult


class BuiltinWebSearchError(RuntimeError):
    """联网搜索失败"""


class BuiltinWebSearch(BaseWebSearch):
    """
    内置联网搜索 Provider

    当前为骨架实现——在问答引擎 (Phase E) 中通过
    WebSearch 和 WebFetch 工具进行实际搜索。

    用法:
        ws = BuiltinWebSearch(settings)
        results = ws.search("2024年绿色数据中心政策")
    """

    def __init__(self, settings: Any, **kwargs: Any):
        self._settings = settings
        self._max_results = settings.web_search.max_results
        self._trusted_domains = settings.web_search.trusted_domains

    def search(
        self,
        query: str,
        max_results: int = 5,
        trusted_domains: Optional[list[str]] = None,
        trace: Optional[Any] = None,
    ) -> list[WebSearchResult]:
        """
        执行联网搜索。

        实现说明:
        - 在完整实现中，会调用 WebSearch 工具获取 URL 列表
        - 然后对每个 URL 调用 WebFetch 提取正文
        - 返回带标题、URL 和摘要的结构化结果

        当前 (Phase B 骨架) 返回空列表。
        """
        # TODO: Phase D - 集成 WebSearch + WebFetch 工具
        max_r = max_results or self._max_results
        domains = trusted_domains or self._trusted_domains

        # 预留: 实际搜索逻辑
        # 1. WebSearch(query=query, allowed_domains=domains) → url列表
        # 2. for url in urls[:max_r]: WebFetch(url=url) → 正文
        # 3. 构建 WebSearchResult 列表

        return []
