"""
智能问答引擎

流程: 问题分类 → 检索 → Prompt 构建 → LLM 生成 → 数值验证 → 返回
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional

from src.libs.llm.base_llm import BaseLLM, Message
from src.retrieval.hybrid_search import HybridSearcher, SearchResult
from src.chat.prompts import (
    DATA_QUERY_SYSTEM_PROMPT,
    PROPOSAL_CONSULT_SYSTEM_PROMPT,
    RAG_PROMPT_TEMPLATE,
)


@dataclass
class ChatResponse:
    answer: str
    evidence: list[dict] = field(default_factory=list)
    disclaimer: str = ""
    mode: str = "data_query"


@dataclass
class Evidence:
    source_type: str      # "database" | "vector" | "web"
    source_name: str
    content_snippet: str


class ChatEngine:
    """智能问答引擎

    用法:
        engine = ChatEngine(llm, searcher, prompts_dir="config/prompts")
        resp = engine.chat("江苏排名第几？")
        resp = engine.chat("这个方案可行吗？", mode="proposal_consult")
    """

    def __init__(self, llm: BaseLLM, searcher: HybridSearcher):
        self.llm = llm
        self.searcher = searcher

        self._prompts = {
            "data_query": DATA_QUERY_SYSTEM_PROMPT,
            "proposal_consult": PROPOSAL_CONSULT_SYSTEM_PROMPT,
        }

    # ------------------------------------------------------------------
    # 主入口
    # ------------------------------------------------------------------

    def chat(
        self,
        query: str,
        history: list[dict] | None = None,
        mode: str = "data_query",
    ) -> ChatResponse:
        """
        处理单轮问答。

        Args:
            query: 用户问题
            history: 对话历史（可选，暂不支持多轮）
            mode: "data_query" | "proposal_consult"

        Returns:
            ChatResponse
        """
        # 1. 问题分类
        classification = self._classify(query)

        # 2. 越界检测
        if classification == "out_of_scope":
            return ChatResponse(
                answer=self._reject_message(query),
                disclaimer="该问题超出系统范围。",
                mode=mode,
            )

        # 3. 检索
        search_result = self.searcher.search(query)

        # 4. 构建 Prompt
        system_prompt = self._prompts.get(mode, self._prompts["data_query"])
        messages = self._build_messages(system_prompt, query, search_result, history)

        # 5. LLM 生成
        raw_answer = self.llm.chat(messages).content

        # 6. 数值验证 + 构建证据
        evidence = self._extract_evidence(raw_answer, search_result)

        # 7. 如果没搜到任何东西，加免责声明
        disclaimer = ""
        if search_result.fusion_count == 0:
            disclaimer = "未在数据库、知识库或联网搜索中找到相关结果。以上回答仅基于大模型常识，非 NAT_FINAL 官方数据。"
        elif search_result.db_count == 0 and classification not in ("out_of_scope",):
            disclaimer = "NAT_FINAL 数据库中未命中精确匹配，以上回答可能来自知识库或联网搜索。"

        return ChatResponse(
            answer=raw_answer,
            evidence=evidence,
            disclaimer=disclaimer,
            mode=mode,
        )

    def chat_stream(self, query: str, mode: str = "data_query"):
        """流式问答（生成器）"""
        classification = self._classify(query)

        if classification == "out_of_scope":
            yield self._reject_message(query)
            return

        search_result = self.searcher.search(query)
        system_prompt = self._prompts.get(mode, self._prompts["data_query"])
        messages = self._build_messages(system_prompt, query, search_result)

        for chunk in self.llm.chat_stream(messages):
            yield chunk.content

    # ------------------------------------------------------------------
    # 问题分类
    # ------------------------------------------------------------------

    def _classify(self, query: str) -> str:
        """分类问题类型 — 仅拦截城市级精确排名查询，其余都放行给 LLM 处理"""
        q = query.strip()

        # 仅拦截: 明确指定城市名+市的精确查询（如"深圳市排名"）
        city_pattern = r"(广州|深圳|杭州|南京|成都|武汉|苏州|郑州|长沙|青岛|大连|厦门|宁波|佛山|东莞|合肥|福州|南宁|贵阳|昆明|拉萨|兰州|西宁|银川|乌鲁木齐|呼和浩特|海口|石家庄|太原|哈尔滨|长春|沈阳|济南|南昌)市"
        if re.search(city_pattern, q) and not re.search(r"(省|自治区|布局|分类|LPA|LISA|趋势|建议|推荐|适合|排名前|全国)", q):
            return "out_of_scope"

        return "normal"

    def _reject_message(self, query: str) -> str:
        """生成拒绝消息"""
        return (
            "抱歉，本系统仅支持**省级**层面的绿色算力评估。"
            "您可以查询目标城市所在省份的整体数据作为参考。"
        )

    # ------------------------------------------------------------------
    # Prompt 构建
    # ------------------------------------------------------------------

    def _build_messages(
        self,
        system_prompt: str,
        query: str,
        search_result: SearchResult,
        history: list[dict] | None = None,
    ) -> list[Message]:
        """构建 LLM 消息列表"""

        # 格式化检索结果
        ctx_parts = []
        for i, hit in enumerate(search_result.hits):
            source_label = {"database": "📊 数据库", "vector": "📄 企划书", "web": "🌐 联网"}.get(
                hit.source, hit.source
            )
            ctx_parts.append(
                f"[{i+1}] {source_label} | {hit.title}\n{hit.content}"
            )

        retrieval_text = "\n\n".join(ctx_parts) if ctx_parts else "（未检索到相关结果）"

        user_content = RAG_PROMPT_TEMPLATE.format(
            system_prompt=system_prompt,
            retrieval_context=retrieval_text,
            user_query=query,
        )

        return [
            Message(role="system", content=system_prompt),
            Message(role="user", content=user_content),
        ]

    # ------------------------------------------------------------------
    # 数值验证 + 证据提取
    # ------------------------------------------------------------------

    def _extract_evidence(self, answer: str, search_result: SearchResult) -> list[dict]:
        """从回答中提取数字，与检索结果对照"""
        evidence = []

        # 提取回答中的浮点数
        numbers_in_answer = set(re.findall(r"\d+\.\d{2,6}", answer))
        numbers_found = set()

        # 检查每个检索结果
        for hit in search_result.hits:
            hit_numbers = set(re.findall(r"\d+\.\d{2,6}", hit.content))
            overlap = numbers_in_answer & hit_numbers
            if overlap:
                numbers_found.update(overlap)
                evidence.append({
                    "source": hit.source,
                    "title": hit.title,
                    "snippet": hit.content[:200],
                    "numbers_matched": list(overlap)[:5],
                })

        # 找出无来源的数字
        orphan_numbers = numbers_in_answer - numbers_found
        if orphan_numbers:
            evidence.append({
                "source": "⚠️ WARNING",
                "title": "以下数字未在检索结果中找到来源",
                "numbers": list(orphan_numbers),
            })

        return evidence
