"""
LLM Reranker — 用大模型对检索结果打分重排

原理: 将 query + 每条 doc 输入 LLM，要求输出相关性分数 (0-1)，
然后按分数降序排列。适合没有专用 Cross-Encoder 模型的场景。
"""

from __future__ import annotations

from typing import Any, Optional

from src.libs.llm.base_llm import BaseLLM, Message
from src.libs.reranker.base_reranker import BaseReranker, RankedDocument


class LLMRerankerError(RuntimeError):
    """LLM Reranker 调用失败"""


RERANK_PROMPT = """判断以下文档与用户问题的相关性，输出 0-1 之间的分数。

评分标准:
- 1.0: 完全匹配，直接回答
- 0.7-0.9: 高度相关
- 0.4-0.6: 部分相关
- 0.0-0.3: 无关

用户问题: {query}

文档内容: {document}

请只输出一个数字（如 0.85），不要输出其他内容。"""


class LLMReranker(BaseReranker):
    """LLM 重排序器

    用法:
        reranker = LLMReranker(llm_provider)
        ranked = reranker.rerank("江苏综合得分？", docs, top_k=5)
    """

    def __init__(self, llm: BaseLLM):
        self._llm = llm

    def rerank(
        self,
        query: str,
        documents: list[str],
        top_k: int = 5,
        **kwargs: Any,
    ) -> list[RankedDocument]:
        if not documents:
            return []

        scored: list[RankedDocument] = []
        for idx, doc in enumerate(documents):
            score = self._score_single(query, doc)
            scored.append(RankedDocument(
                content=doc,
                score=score,
                index=idx,
            ))

        # 按分数降序，取 top_k
        scored.sort(key=lambda x: x.score, reverse=True)
        return scored[:top_k]

    def _score_single(self, query: str, document: str) -> float:
        prompt = RERANK_PROMPT.format(query=query, document=document[:2000])
        try:
            resp = self._llm.chat(
                messages=[Message(role="user", content=prompt)],
                temperature=0.0,
            )
            # 尝试从回复中提取数字
            import re
            match = re.search(r"(\d+\.?\d*)", resp.content.strip())
            if match:
                score = float(match.group(1))
                return max(0.0, min(1.0, score))  # clamp to [0, 1]
            return 0.0
        except Exception:
            return 0.0
