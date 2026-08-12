"""
标准答案准确性评估 (H4)

将 LLM 生成的回答与 Golden Set 标准答案进行逐题比对，
评估回答中事实性陈述（排名、得分、省份列表、布局类型等）是否准确。

与 H2 的差异：H2 只检查关键词**存在与否**，H4 检查数字/列表/类型**是否正确**。
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from src.data.queries import QueryEngine
from src.evaluation.test_questions import TEST_QUESTIONS


@dataclass
class StandardAnswerResult:
    """单题标准答案评估结果"""
    question_id: str
    question: str
    passed: bool
    accuracy_score: float = 0.0      # 0-1
    checks_passed: int = 0
    checks_total: int = 0
    details: str = ""
    extracted_value: str = ""        # 从 LLM 回答中提取的值
    expected_value: str = ""         # Golden Set 标准值


@dataclass
class StandardAnswerSuite:
    """标准答案评估套件"""
    total: int = 0
    passed: int = 0
    results: list[StandardAnswerResult] = field(default_factory=list)
    overall_accuracy: float = 0.0

    @property
    def pass_rate(self) -> float:
        return self.passed / self.total if self.total > 0 else 0


class QAStandardEvaluator:
    """标准答案准确性评估器

    对每道测试题，从 LLM 回答中提取关键事实值，
    与 Golden Set 数据库中的标准答案进行比对。

    用法:
        evaluator = QAStandardEvaluator(query_engine, chat_engine)
        suite = evaluator.run_all()
    """

    def __init__(self, query_engine: QueryEngine, chat_engine):
        self.qe = query_engine
        self.engine = chat_engine

    # ------------------------------------------------------------------
    # 主入口
    # ------------------------------------------------------------------

    def run_all(self) -> StandardAnswerSuite:
        suite = StandardAnswerSuite(total=len(TEST_QUESTIONS))

        evaluators = {
            "Q1": self._eval_q1,
            "Q2": self._eval_q2,
            "Q3": self._eval_q3,
            "Q4": self._eval_q4,
            "Q5": self._eval_q5,
            "Q6": self._eval_q6,
            "Q7": self._eval_q7,
            "Q8": self._eval_q8,
            "Q9": self._eval_q9,
            "Q10": self._eval_q10,
        }

        for tq in TEST_QUESTIONS:
            qid = tq["id"]
            try:
                resp = self.engine.chat(tq["question"], mode=tq.get("mode", "data_query"))
                eval_fn = evaluators.get(qid)
                if eval_fn:
                    result = eval_fn(resp.answer, tq)
                else:
                    result = StandardAnswerResult(
                        question_id=qid, question=tq["question"],
                        passed=True, details="无标准答案评估逻辑",
                    )
                suite.results.append(result)
                if result.passed:
                    suite.passed += 1
            except Exception as e:
                suite.results.append(StandardAnswerResult(
                    question_id=qid, question=tq["question"],
                    passed=False, details=f"引擎调用失败: {e}",
                ))

        if suite.results:
            suite.overall_accuracy = sum(r.accuracy_score for r in suite.results) / len(suite.results)

        return suite

    # ------------------------------------------------------------------
    # 逐题评估
    # ------------------------------------------------------------------

    def _eval_q1(self, answer: str, tq: dict) -> StandardAnswerResult:
        """江苏排名第几？— 期望：排名=1, 得分≈0.5733"""
        checks = 0
        checks_passed = 0
        extracted = []

        # 获取标准答案
        try:
            summary = self.qe.get_province_summary("江苏")
            expected_rank = summary.score_rank
            expected_score = summary.composite_score
        except Exception:
            return StandardAnswerResult(
                question_id="Q1", question=tq["question"],
                passed=False, details="无法查询 DB 标准答案",
            )

        # 检查 1: 排名
        checks += 1
        rank_patterns = [r"第\s*(\d+)\s*名", r"排名\s*第?\s*(\d+)", r"排名(\d+)"]
        found_rank = None
        for pat in rank_patterns:
            m = re.search(pat, answer)
            if m:
                found_rank = int(m.group(1))
                break
        # 也接受直接数字在"排名"附近
        if found_rank is None:
            m = re.search(r"排名.*?(\d+)", answer)
            if m:
                found_rank = int(m.group(1))

        if found_rank == expected_rank:
            checks_passed += 1
            extracted.append(f"排名={found_rank}")
        else:
            extracted.append(f"排名={found_rank}(期望{expected_rank})")

        # 检查 2: 得分
        checks += 1
        score_match = re.search(r"(\d+\.\d{2,4})", answer)
        found_score = float(score_match.group(1)) if score_match else None
        if found_score and abs(found_score - expected_score) < 0.01:
            checks_passed += 1
            extracted.append(f"得分={found_score:.4f}")
        else:
            extracted.append(f"得分={found_score}(期望~{expected_score:.4f})")

        return StandardAnswerResult(
            question_id="Q1", question=tq["question"],
            passed=checks_passed == checks,
            accuracy_score=checks_passed / checks if checks else 0,
            checks_passed=checks_passed, checks_total=checks,
            extracted_value="; ".join(extracted),
            expected_value=f"排名{expected_rank}, 得分{expected_score:.4f}",
            details="全部正确" if checks_passed == checks else "存在偏差",
        )

    def _eval_q2(self, answer: str, tq: dict) -> StandardAnswerResult:
        """广东 vs 浙江哪个得分更高？— 期望：广东更高"""
        checks = 0
        checks_passed = 0

        try:
            gd = self.qe.get_province_summary("广东")
            zj = self.qe.get_province_summary("浙江")
        except Exception:
            return StandardAnswerResult(
                question_id="Q2", question=tq["question"],
                passed=False, details="无法查询 DB",
            )

        # 检查 1: 答案明确指出广东更高
        checks += 1
        if "广东" in answer and ("更高" in answer or "领先" in answer or "优于" in answer or "高于" in answer):
            checks_passed += 1

        # 检查 2: 广东得分在答案中
        checks += 1
        if f"{gd.composite_score:.4f}"[:4] in answer:
            checks_passed += 1

        # 检查 3: 浙江得分在答案中
        checks += 1
        if f"{zj.composite_score:.4f}"[:4] in answer:
            checks_passed += 1

        return StandardAnswerResult(
            question_id="Q2", question=tq["question"],
            passed=checks_passed >= 2,
            accuracy_score=checks_passed / checks if checks else 0,
            checks_passed=checks_passed, checks_total=checks,
            extracted_value=f"广东{gd.composite_score:.4f}, 浙江{zj.composite_score:.4f}",
            expected_value=f"广东更高 ({gd.composite_score:.4f} > {zj.composite_score:.4f})",
            details="全部正确" if checks_passed == checks else "部分正确",
        )

    def _eval_q3(self, answer: str, tq: dict) -> StandardAnswerResult:
        """高适宜综合承载区有哪些省份？— 期望：5省列表正确"""
        checks = 0
        checks_passed = 0

        expected = self.qe.get_provinces_by_layout("高适宜综合承载区")

        # 检查 1: 提及省份数量
        checks += 1
        if str(len(expected)) in answer:
            checks_passed += 1

        # 检查 2-6: 每个省份都在答案中
        for prov in expected:
            checks += 1
            if prov in answer:
                checks_passed += 1

        return StandardAnswerResult(
            question_id="Q3", question=tq["question"],
            passed=checks_passed >= checks * 0.8,  # 80% 省份正确即通过
            accuracy_score=checks_passed / checks if checks else 0,
            checks_passed=checks_passed, checks_total=checks,
            extracted_value=f"{checks_passed-1}/{len(expected)}省正确",
            expected_value="、".join(expected),
            details="全部正确" if checks_passed == checks else f"{(checks-checks_passed)}省遗漏或错误",
        )

    def _eval_q4(self, answer: str, tq: dict) -> StandardAnswerResult:
        """北京历年趋势？— 期望：提到2016-2024，趋势上升"""
        checks = 0
        checks_passed = 0

        # 检查 1: 提到年份范围
        checks += 1
        if "2016" in answer and "2024" in answer:
            checks_passed += 1

        # 检查 2: 上升趋势
        checks += 1
        trend_words = ["上升", "增长", "提升", "改善", "进步", "提高"]
        if any(w in answer for w in trend_words):
            checks_passed += 1

        # 检查 3: 包含具体得分数字
        checks += 1
        if re.search(r"\d+\.\d+", answer):
            checks_passed += 1

        return StandardAnswerResult(
            question_id="Q4", question=tq["question"],
            passed=checks_passed >= 2,
            accuracy_score=checks_passed / checks if checks else 0,
            checks_passed=checks_passed, checks_total=checks,
            details="全部正确" if checks_passed == checks else "部分正确",
        )

    def _eval_q5(self, answer: str, tq: dict) -> StandardAnswerResult:
        """边界省份有哪些？— 期望：提到四川，解释边界概念"""
        checks = 0
        checks_passed = 0

        # 检查 1: 提到关键省份
        checks += 1
        boundary = self.qe.get_boundary_provinces()
        boundary_names = [b["province"] for b in boundary]
        if any(p in answer for p in boundary_names):
            checks_passed += 1

        # 检查 2: 提到边界概念
        checks += 1
        if "边界" in answer:
            checks_passed += 1

        # 检查 3: 提到保持原布局概率或布局边界
        checks += 1
        if "保持" in answer or "概率" in answer or "布局边界" in answer:
            checks_passed += 1

        return StandardAnswerResult(
            question_id="Q5", question=tq["question"],
            passed=checks_passed >= 2,
            accuracy_score=checks_passed / checks if checks else 0,
            checks_passed=checks_passed, checks_total=checks,
            extracted_value=f"提及{sum(1 for p in boundary_names if p in answer)}/{len(boundary_names)}边界省",
            expected_value="、".join(boundary_names),
            details="全部正确" if checks_passed == checks else "部分正确",
        )

    def _eval_q6(self, answer: str, tq: dict) -> StandardAnswerResult:
        """城市级查询应被拒绝"""
        reject_keywords = ["抱歉", "不支持", "超出", "无法", "不能回答", "省级"]

        return StandardAnswerResult(
            question_id="Q6", question=tq["question"],
            passed=any(kw in answer for kw in reject_keywords),
            accuracy_score=1.0 if any(kw in answer for kw in reject_keywords) else 0.0,
            checks_passed=1 if any(kw in answer for kw in reject_keywords) else 0,
            checks_total=1,
            extracted_value="已拒绝" if any(kw in answer for kw in reject_keywords) else "未拒绝",
            expected_value="应拒绝城市级查询",
            details="正确拒绝" if any(kw in answer for kw in reject_keywords) else "未正确拒绝（越界检测失败）",
        )

    def _eval_q7(self, answer: str, tq: dict) -> StandardAnswerResult:
        """LISA显著省份？— 期望：列出关键省份 + 术语合规"""
        checks = 0
        checks_passed = 0

        # 检查 1: 提到关键 LISA 省份
        checks += 1
        key_provs = ["上海", "江苏", "内蒙古", "广东", "福建"]
        found = sum(1 for p in key_provs if p in answer)
        if found >= 3:
            checks_passed += 1

        # 检查 2: 术语合规 - 无"确定性"
        checks += 1
        if "确定性" not in answer:
            checks_passed += 1

        # 检查 3: 提到"探索性" 或 LISA 概念
        checks += 1
        if "探索性" in answer or "LISA" in answer or "空间" in answer:
            checks_passed += 1

        return StandardAnswerResult(
            question_id="Q7", question=tq["question"],
            passed=checks_passed >= 2,
            accuracy_score=checks_passed / checks if checks else 0,
            checks_passed=checks_passed, checks_total=checks,
            extracted_value=f"提及{found}/{len(key_provs)}关键省",
            expected_value="、".join(key_provs),
            details="全部正确" if checks_passed == checks else "部分正确",
        )

    def _eval_q8(self, answer: str, tq: dict) -> StandardAnswerResult:
        """贵州布局类型？— 期望：能源低碳优势承接区"""
        checks = 0
        checks_passed = 0

        try:
            summary = self.qe.get_province_summary("贵州")
            expected_layout = summary.layout_type
        except Exception:
            expected_layout = "能源低碳优势承接区"

        # 检查 1: 布局类型正确
        checks += 1
        if expected_layout in answer:
            checks_passed += 1

        # 检查 2: 提到贵州
        checks += 1
        if "贵州" in answer:
            checks_passed += 1

        return StandardAnswerResult(
            question_id="Q8", question=tq["question"],
            passed=checks_passed == checks,
            accuracy_score=checks_passed / checks if checks else 0,
            checks_passed=checks_passed, checks_total=checks,
            extracted_value=expected_layout if expected_layout in answer else "类型错误",
            expected_value=expected_layout,
            details="全部正确" if checks_passed == checks else "布局类型错误",
        )

    def _eval_q9(self, answer: str, tq: dict) -> StandardAnswerResult:
        """影响因素？— 期望：提到7个维度"""
        checks = 0
        checks_passed = 0

        # 检查 1: 提到7个维度
        checks += 1
        if "7" in answer and ("维度" in answer or "方面" in answer):
            checks_passed += 1

        # 检查 2: 提到至少3个具体维度
        checks += 1
        dims = ["算力需求", "数字基础设施", "能源供给", "绿色低碳",
                "气候", "创新", "人才", "区域协同"]
        found_dims = sum(1 for d in dims if d in answer)
        if found_dims >= 3:
            checks_passed += 1

        # 检查 3: 提到34项指标
        checks += 1
        if "34" in answer or "指标" in answer:
            checks_passed += 1

        return StandardAnswerResult(
            question_id="Q9", question=tq["question"],
            passed=checks_passed >= 2,
            accuracy_score=checks_passed / checks if checks else 0,
            checks_passed=checks_passed, checks_total=checks,
            extracted_value=f"提及{found_dims}/7维度",
            expected_value="7维度34指标",
            details="全部正确" if checks_passed == checks else "部分正确",
        )

    def _eval_q10(self, answer: str, tq: dict) -> StandardAnswerResult:
        """适合建绿色数据中心？— 期望：提到高适宜 + 能源低碳"""
        checks = 0
        checks_passed = 0

        # 检查 1: 提到高适宜承载区
        checks += 1
        if "高适宜" in answer:
            checks_passed += 1

        # 检查 2: 提到能源或低碳
        checks += 1
        if "能源" in answer or "低碳" in answer:
            checks_passed += 1

        # 检查 3: 提到布局
        checks += 1
        if "布局" in answer or "承载" in answer or "承接" in answer:
            checks_passed += 1

        return StandardAnswerResult(
            question_id="Q10", question=tq["question"],
            passed=checks_passed >= 2,
            accuracy_score=checks_passed / checks if checks else 0,
            checks_passed=checks_passed, checks_total=checks,
            details="全部正确" if checks_passed == checks else "部分正确",
        )
