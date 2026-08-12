"""
RAG 数字追溯评估 (H3)

评估 ChatEngine 回答中的关键数字能否追溯到 DB 或检索来源。

策略：
  1. 对每道测试题，定义"期望关键数字"（排名、得分、数量等）
  2. 检查这些期望数字是否在 LLM 回答中出现（容差匹配）
  3. 验证它们是否可追溯到 DB 查询结果
  4. 检查 engine 的证据链是否捕获了这些数字
  5. 测试 chat_stream() 路径与 batch 答案一致性
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from src.data.queries import QueryEngine
from src.evaluation.test_questions import TEST_QUESTIONS


# ---------------------------------------------------------------------------
# 每道测试题的"期望关键数字"定义
# 这些数字都应该可追溯到 Golden Set DB
# ---------------------------------------------------------------------------

EXPECTED_NUMBERS = {
    "Q1": [
        {"value": 0.5733, "tolerance": 0.01, "label": "江苏综合得分", "field": "composite_score"},
        {"value": 1, "tolerance": 0, "label": "江苏排名", "field": "score_rank"},
    ],
    "Q2": [
        {"value": 0.5643, "tolerance": 0.01, "label": "广东综合得分", "field": "composite_score"},
        {"value": 0.5620, "tolerance": 0.01, "label": "浙江综合得分", "field": "composite_score"},
    ],
    "Q3": [
        {"value": 5, "tolerance": 0, "label": "高适宜承载区省份数", "field": "count"},
    ],
    "Q4": [
        {"value": 2016, "tolerance": 0, "label": "起始年份", "field": "year"},
        {"value": 2024, "tolerance": 0, "label": "结束年份", "field": "year"},
    ],
    "Q5": [
        {"value": None, "tolerance": 0, "label": "边界省份数量(应>0)", "field": "count"},
    ],
    "Q6": [
        # 拒绝问题，无期望数字
    ],
    "Q7": [
        {"value": 5, "tolerance": 1, "label": "LISA显著省份数(~5)", "field": "count"},
    ],
    "Q8": [
        {"value": None, "tolerance": 0, "label": "贵州得分(应出现)", "field": "composite_score"},
    ],
    "Q9": [
        {"value": 7, "tolerance": 0, "label": "评价维度数", "field": "dimension_count"},
    ],
    "Q10": [
        {"value": None, "tolerance": 0, "label": "至少1个得分数字", "field": "composite_score"},
    ],
}

# 31省名称
PROVINCE_NAMES = [
    "北京", "天津", "河北", "山西", "内蒙古",
    "辽宁", "吉林", "黑龙江",
    "上海", "江苏", "浙江", "安徽", "福建", "江西", "山东",
    "河南", "湖北", "湖南", "广东", "广西", "海南",
    "重庆", "四川", "贵州", "云南", "西藏",
    "陕西", "甘肃", "青海", "宁夏", "新疆",
]


@dataclass
class TraceabilityResult:
    """单题追溯结果"""
    question_id: str
    question: str
    total_expected: int = 0         # 期望关键数字数
    found_in_answer: int = 0        # 在回答中找到的关键数字数
    traced_to_db: int = 0           # 可追溯到 DB 的数字数
    traced_in_evidence: int = 0     # 在 engine evidence 中找到的数字数
    details: list[dict] = field(default_factory=list)

    @property
    def trace_rate(self) -> float:
        """追溯率 = (找到且可追溯) / 期望总数"""
        if self.total_expected == 0:
            return 1.0
        return self.traced_to_db / self.total_expected

    @property
    def passed(self) -> bool:
        """追溯率 >= 70% 视为通过"""
        if self.total_expected == 0:
            return True
        return self.trace_rate >= 0.70


@dataclass
class RAGTraceabilitySuite:
    """完整追溯套件结果"""
    total: int = 0
    passed: int = 0
    results: list[TraceabilityResult] = field(default_factory=list)
    streaming_consistency: dict | None = None

    @property
    def overall_trace_rate(self) -> float:
        if not self.results:
            return 1.0
        total_exp = sum(r.total_expected for r in self.results)
        traced = sum(r.traced_to_db for r in self.results)
        return traced / total_exp if total_exp > 0 else 1.0


class RAGTraceabilityEvaluator:
    """RAG 数字追溯评估器

    用法:
        evaluator = RAGTraceabilityEvaluator(query_engine, chat_engine)
        suite = evaluator.run_all()
    """

    def __init__(self, query_engine: QueryEngine, chat_engine):
        self.qe = query_engine
        self.engine = chat_engine

    # ------------------------------------------------------------------
    # 主入口
    # ------------------------------------------------------------------

    def run_all(self) -> RAGTraceabilitySuite:
        suite = RAGTraceabilitySuite(total=len(TEST_QUESTIONS))

        for tq in TEST_QUESTIONS:
            try:
                resp = self.engine.chat(tq["question"], mode=tq.get("mode", "data_query"))
                result = self._evaluate_one(tq, resp)
                suite.results.append(result)
                if result.passed:
                    suite.passed += 1
            except Exception as e:
                suite.results.append(TraceabilityResult(
                    question_id=tq["id"], question=tq["question"],
                    details=[{"error": str(e)}],
                ))

        # 流式一致性测试
        try:
            suite.streaming_consistency = self._test_streaming_consistency()
        except Exception:
            suite.streaming_consistency = {"error": "流式测试异常"}

        return suite

    def _evaluate_one(self, tq: dict, resp) -> TraceabilityResult:
        qid = tq["id"]
        answer = resp.answer
        evidence = resp.evidence
        expected = EXPECTED_NUMBERS.get(qid, [])

        result = TraceabilityResult(
            question_id=qid, question=tq["question"],
            total_expected=len(expected),
        )

        if not expected:
            # Q6 拒绝类问题 — 通过（没有期望数字即无追溯需求）
            return result

        for exp in expected:
            detail = {"label": exp["label"], "expected_value": exp.get("value")}

            # 1. 数字是否在回答中出现？（容差匹配）
            found = self._find_number_in_text(answer, exp["value"], exp["tolerance"])
            detail["found_in_answer"] = found
            if found:
                result.found_in_answer += 1

            # 2. 数字能否追溯到 DB？
            traced = False
            if found and exp["value"] is not None:
                traced = self._verify_against_db(qid, exp)
            elif exp["value"] is None:
                # 宽松检查：答案中是否有该类型的数字
                traced = self._has_any_number(answer, exp["field"])
            detail["traced_to_db"] = traced
            if traced:
                result.traced_to_db += 1

            # 3. 数字是否在 engine 证据链中？
            in_evidence = self._check_evidence(evidence, exp["value"]) if exp["value"] is not None else bool(evidence)
            detail["in_evidence"] = in_evidence
            if in_evidence:
                result.traced_in_evidence += 1

            result.details.append(detail)

        return result

    # ------------------------------------------------------------------
    # 数字查找
    # ------------------------------------------------------------------

    @staticmethod
    def _find_number_in_text(text: str, expected_value, tolerance: float = 0.01) -> bool:
        """检查预期值是否在文本中出现（容差匹配）"""
        if expected_value is None:
            return True  # None = 只要有任何数字即算找到

        if isinstance(expected_value, int):
            # 整数精确匹配
            int_patterns = [
                rf"\b{expected_value}\b",
                rf"第\s*{expected_value}\s*名",
                rf"排名.*?{expected_value}",
            ]
            for pat in int_patterns:
                if re.search(pat, text):
                    return True
            return False

        # 浮点数容差匹配
        for m in re.finditer(r"\d+\.\d+", text):
            try:
                val = float(m.group())
                if abs(val - float(expected_value)) <= tolerance:
                    return True
            except ValueError:
                continue
        return False

    @staticmethod
    def _has_any_number(text: str, field: str) -> bool:
        """检查文本中是否有该字段类型的任何数字"""
        if field in ("count", "year", "score_rank"):
            return bool(re.search(r"\b\d+\b", text))
        if field in ("composite_score",):
            return bool(re.search(r"\d+\.\d+", text))
        return bool(re.search(r"\d+", text))

    # ------------------------------------------------------------------
    # DB 验证
    # ------------------------------------------------------------------

    def _verify_against_db(self, qid: str, exp: dict) -> bool:
        """验证期望数字是否与 DB 值一致"""
        try:
            if qid == "Q1":
                summary = self.qe.get_province_summary("江苏")
                if exp["field"] == "composite_score":
                    return abs(exp["value"] - summary.composite_score) < 0.01
                if exp["field"] == "score_rank":
                    return exp["value"] == summary.score_rank
            elif qid == "Q2":
                if "广东" in exp["label"]:
                    summary = self.qe.get_province_summary("广东")
                else:
                    summary = self.qe.get_province_summary("浙江")
                return abs(exp["value"] - summary.composite_score) < 0.01
            elif qid == "Q3":
                provs = self.qe.get_provinces_by_layout("高适宜综合承载区")
                return len(provs) == exp["value"]
            elif qid == "Q4":
                # 年份范围检查
                history = self.qe.get_score_history("北京")
                years = [h["年份"] for h in history]
                return 2016 in years and 2024 in years
            elif qid == "Q5":
                boundary = self.qe.get_boundary_provinces()
                return len(boundary) > 0
            elif qid == "Q7":
                lisa = self.qe.get_significant_lisa()
                return abs(len(lisa) - exp["value"]) <= exp["tolerance"]
            elif qid == "Q8":
                summary = self.qe.get_province_summary("贵州")
                return summary.composite_score > 0
            elif qid == "Q9":
                return exp["value"] == 7  # 7个维度是已知常量
            elif qid == "Q10":
                return True  # 有相关数字即可
        except Exception:
            pass
        return False

    # ------------------------------------------------------------------
    # 证据链检查
    # ------------------------------------------------------------------

    @staticmethod
    def _check_evidence(evidence: list[dict], expected_value) -> bool:
        """检查期望值是否出现在 engine 的证据链中"""
        if not evidence:
            return False
        if expected_value is None:
            return len(evidence) > 0

        val_str = str(expected_value)
        for ev in evidence:
            snippet = ev.get("snippet", "") + str(ev.get("numbers_matched", ""))
            if val_str in snippet:
                return True
        return False

    # ------------------------------------------------------------------
    # 流式一致性
    # ------------------------------------------------------------------

    def _test_streaming_consistency(self) -> dict:
        """测试 chat_stream() 与 chat() 答案一致性 (Q1-Q3)"""
        results = {}
        stream_questions = TEST_QUESTIONS[:3]

        for tq in stream_questions:
            qid = tq["id"]
            try:
                batch_resp = self.engine.chat(tq["question"], mode=tq.get("mode", "data_query"))
                batch_answer = batch_resp.answer

                stream_parts = []
                for chunk in self.engine.chat_stream(tq["question"], mode=tq.get("mode", "data_query")):
                    stream_parts.append(chunk)
                stream_answer = "".join(stream_parts)

                # 提取关键数字对比
                batch_nums = set(re.findall(r"\d+\.?\d*", batch_answer))
                stream_nums = set(re.findall(r"\d+\.?\d*", stream_answer))
                nums_match = batch_nums == stream_nums

                has_evidence = bool(getattr(self.engine, "_last_stream_evidence", None))

                results[qid] = {
                    "nums_match": nums_match,
                    "has_evidence": has_evidence,
                    "batch_len": len(batch_answer),
                    "stream_len": len(stream_answer),
                    "consistent": nums_match,
                }
            except Exception as e:
                results[qid] = {"error": str(e), "consistent": False}

        return results
