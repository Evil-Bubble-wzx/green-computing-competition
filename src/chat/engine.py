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
        """流式问答（生成器）— 完整响应后提取证据"""
        self._last_stream_evidence = []
        classification = self._classify(query)

        if classification == "out_of_scope":
            yield self._reject_message(query)
            return

        search_result = self.searcher.search(query)
        system_prompt = self._prompts.get(mode, self._prompts["data_query"])
        messages = self._build_messages(system_prompt, query, search_result)

        full_answer_parts = []
        for chunk in self.llm.chat_stream(messages):
            full_answer_parts.append(chunk.content)
            yield chunk.content

        # 流式响应完成后提取证据
        full_answer = "".join(full_answer_parts)
        evidence = self._extract_evidence(full_answer, search_result)
        # 将证据挂载为生成器的属性，调用方可通过 .evidence 获取
        self._last_stream_evidence = evidence

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
        """从回答中提取所有数字（整数+浮点数），与检索结果和 DB 对照"""
        evidence = []

        # 提取回答中的所有数字：浮点数 + 独立整数
        floats_in_answer = set(re.findall(r"\d+\.\d+", answer))
        ints_in_answer = set(re.findall(r"(?<!\d\.)(?<!\d)\b\d+\b(?!\.?\d)", answer))
        all_numbers = floats_in_answer | ints_in_answer

        # 与检索结果交叉比对
        numbers_found: set[str] = set()
        for hit in search_result.hits:
            hit_floats = set(re.findall(r"\d+\.\d+", hit.content))
            hit_ints = set(re.findall(r"(?<!\d\.)(?<!\d)\b\d+\b(?!\.?\d)", hit.content))
            hit_all = hit_floats | hit_ints
            overlap = all_numbers & hit_all
            if overlap:
                numbers_found.update(overlap)
                evidence.append({
                    "source": hit.source,
                    "title": hit.title,
                    "snippet": hit.content[:200],
                    "numbers_matched": list(overlap)[:5],
                })

        # 找出无来源的数字
        orphan_numbers = all_numbers - numbers_found

        # DB 行级追溯：对无来源数字尝试精确 DB 验证
        if orphan_numbers:
            db_traces = self._trace_to_db(answer)
            for trace in db_traces:
                num_str = str(trace.get("answer_value", ""))
                if num_str in orphan_numbers:
                    orphan_numbers.discard(num_str)
                    numbers_found.add(num_str)
                    evidence.append({
                        "source": "database",
                        "title": f"DB验证: {trace.get('province', '')}.{trace.get('field', '')}",
                        "snippet": f"回答值={trace.get('answer_value')} DB值={trace.get('db_value')} 匹配={trace.get('match')}",
                        "numbers_matched": [num_str],
                        "db_trace": trace,
                    })

        # 孤儿数字警告
        if orphan_numbers:
            evidence.append({
                "source": "⚠️ WARNING",
                "title": "以下数字未在检索结果或数据库中找到来源",
                "numbers": list(orphan_numbers),
            })

        return evidence

    def _trace_to_db(self, answer: str) -> list[dict]:
        """将回答中的数字追溯到数据库具体行/字段

        策略：
          1. 检测回答中的省份名称
          2. 检测回答中的字段关键词
          3. 查询 DB 验证数字是否匹配
        """
        traces = []

        # 31省名称列表
        province_names = [
            "北京", "天津", "河北", "山西", "内蒙古",
            "辽宁", "吉林", "黑龙江",
            "上海", "江苏", "浙江", "安徽", "福建", "江西", "山东",
            "河南", "湖北", "湖南", "广东", "广西", "海南",
            "重庆", "四川", "贵州", "云南", "西藏",
            "陕西", "甘肃", "青海", "宁夏", "新疆",
        ]

        # 字段关键词 → DB 列名/查询方法
        field_patterns = [
            (r"(?:综合|复合)?得分", "composite_score"),
            (r"(?:全国)?排名", "score_rank"),
            (r"适宜度排名", "suit_rank"),
            (r"综合适宜度", "suitability"),
            (r"布局类型", "layout_type"),
            (r"LPA|潜在类别", "lpa_type_name"),
            (r"稳定性标签", "stability_label"),
            (r"LISA", "lisa_type_2024"),
            (r"绿色数据中心", "green_dc_count_2023"),
            (r"枢纽", "is_hub"),
            (r"保持.*布局概率|保持原布局", "keep_baseline_prob"),
            (r"阶段增量", "growth"),
            (r"需求网络", "demand_idx"),
            (r"能源低碳", "energy_idx"),
            (r"约束压力", "constraint_idx"),
        ]

        # 找到回答中提到的省份
        found_provinces = [p for p in province_names if p in answer]

        # 如果没找到省份，尝试通用数字验证
        if not found_provinces:
            # 检查是否有布局类型、计数等全局查询
            for pattern, field in field_patterns:
                if re.search(pattern, answer):
                    # 提取附近的数字
                    numbers = re.findall(r"\d+\.?\d*", answer)
                    for num in numbers[:3]:
                        traces.append({
                            "province": "(全局)", "field": field,
                            "answer_value": num, "db_value": None, "match": None,
                            "note": "无省份上下文，无法精确追溯",
                        })
            return traces

        # 对每个省份进行追溯
        for province in found_provinces[:5]:  # 最多追溯5个省份
            try:
                summary = self.searcher.query_engine.get_province_summary(province)
            except Exception:
                continue

            # 将 ProvinceSummary 转为 dict
            summary_dict = {
                "composite_score": summary.composite_score,
                "score_rank": summary.score_rank,
                "layout_type": summary.layout_type,
                "lpa_type_name": summary.lpa_type_name,
                "stability_label": summary.stability_label,
                "lisa_type_2024": summary.lisa_type_2024,
                "is_hub": summary.is_hub,
                "green_dc_count_2023": summary.green_dc_count_2023,
                "keep_baseline_prob": summary.keep_baseline_prob,
            }

            # 为检测到的字段提取数字并比对
            for pattern, field in field_patterns:
                if field not in summary_dict:
                    continue
                db_val = summary_dict[field]

                # 提取该字段附近的数字
                field_match = re.search(pattern + r".*?(\d+\.?\d*)", answer)
                if not field_match:
                    field_match = re.search(r"(\d+\.?\d*).*?" + pattern, answer)

                if field_match:
                    answer_num = field_match.group(1)
                    match = self._compare_values(answer_num, db_val)
                    traces.append({
                        "province": province, "field": field,
                        "answer_value": answer_num, "db_value": str(db_val),
                        "match": match,
                    })

        return traces

    @staticmethod
    def _compare_values(answer_str: str, db_value) -> bool:
        """比较回答中的数字与 DB 值"""
        try:
            answer_float = float(answer_str)
            if isinstance(db_value, bool):
                return (answer_float == 1.0 and db_value) or (answer_float == 0.0 and not db_value)
            if isinstance(db_value, (int, float)):
                return abs(answer_float - float(db_value)) < 0.01
            if isinstance(db_value, str):
                return answer_str in db_value or db_value in answer_str
        except ValueError:
            return str(db_value) in answer_str or answer_str in str(db_value)
        return False
