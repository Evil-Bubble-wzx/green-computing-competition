"""
问答质量评估 (H2)

10 道测试题，评估 ChatEngine 的:
  - 数值准确率 (目标 100%)
  - 术语合规率 (目标 100%)
  - 越界拒绝率 (目标 100%)
  - 证据可追溯率 (目标 100%)
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from src.evaluation.test_questions import TEST_QUESTIONS


@dataclass
class QAResult:
    """单题评估结果"""
    question_id: str
    passed: bool
    accuracy: bool = True      # 数字是否都在检索结果中
    terminology: bool = True   # 是否有违规术语
    rejection: bool = False    # 是否正确拒绝
    details: str = ""


@dataclass
class QASuiteResult:
    """完整评估套件结果"""
    total: int = 0
    passed: int = 0
    results: list[QAResult] = field(default_factory=list)

    @property
    def pass_rate(self) -> float:
        return self.passed / self.total if self.total > 0 else 0


class QAQualityEvaluator:
    """问答质量评估器

    用法:
        evaluator = QAQualityEvaluator(chat_engine)
        result = evaluator.run_all()
    """

    # 术语禁止词
    FORBIDDEN_TERMS = [
        ("LISA", ["显著集聚", "确定性空间", "强空间自相关"]),
        ("SHAP", ["因果", "预测能力", "决定因素"]),
        ("LPA", ["客观类型", "真实类别", "绝对类型"]),
        ("预测", ["未来5年", "将会达到", "必然趋势"]),
        ("枢纽", ["外部验证", "独立验证"]),
    ]

    def __init__(self, chat_engine):
        self.engine = chat_engine

    def run_all(self) -> QASuiteResult:
        """运行全部 10 道测试题"""
        suite = QASuiteResult(total=len(TEST_QUESTIONS))

        for tq in TEST_QUESTIONS:
            try:
                resp = self.engine.chat(tq["question"], mode=tq.get("mode", "data_query"))
                result = self._evaluate_one(tq, resp.answer)
                suite.results.append(result)
                if result.passed:
                    suite.passed += 1
            except Exception as e:
                suite.results.append(QAResult(
                    question_id=tq["id"], passed=False,
                    details=f"引擎调用失败: {e}",
                ))

        return suite

    def _evaluate_one(self, tq: dict, answer: str) -> QAResult:
        qid = tq["id"]
        issues = []

        # 1. 越界检测
        if tq.get("should_reject"):
            reject_keywords = ["抱歉", "不支持", "超出", "无法", "不能回答"]
            if any(kw in answer for kw in reject_keywords):
                return QAResult(question_id=qid, passed=True, rejection=True, details="正确拒绝")
            else:
                return QAResult(question_id=qid, passed=False,
                                details="应拒绝但未拒绝（越界检测失败）")

        # 2. 数字检查
        for num in tq.get("expect_numbers", []):
            if num not in answer:
                issues.append(f"缺少预期数字: {num}")

        # 3. 关键词检查
        for kw in tq.get("expect_keywords", []):
            if kw not in answer:
                issues.append(f"缺少关键词: {kw}")

        # 4. 禁止词检查
        for kw in tq.get("forbidden", []):
            if kw in answer:
                issues.append(f"出现禁止词: {kw}")

        # 5. 术语合规
        for category, terms in self.FORBIDDEN_TERMS:
            for term in terms:
                if term in answer:
                    issues.append(f"术语违规 [{category}]: {term}")

        # 6. 证据检查
        has_evidence = bool(re.search(r"(NAT_FINAL|2024|数据来源|检索结果)", answer))
        if not has_evidence:
            issues.append("缺少数据来源引用")

        passed = len(issues) == 0
        return QAResult(
            question_id=qid,
            passed=passed,
            accuracy=all("数字" not in i for i in issues),
            terminology=all("术语" not in i for i in issues),
            details="; ".join(issues) if issues else "全部通过",
        )
