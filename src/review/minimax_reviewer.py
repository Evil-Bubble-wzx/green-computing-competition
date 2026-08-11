"""
MiniMax 评审器

调用 MiniMax-M3 模型对企划书建议报告进行评分和反馈。
循环评审直到分数 ≥ 8 分（满分 10 分）。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


REVIEW_SYSTEM_PROMPT = """\
你是一个严格的绿色算力企划书评审专家。你需要对一份企划书咨询建议报告进行评分。

## 评分维度（每项 0-10 分，总分取平均）

| 维度 | 评分标准 |
|------|---------|
| 数据准确性 | 报告中的数字是否与 NAT_FINAL 数据一致？有无编造痕迹？ |
| 分析深度 | 是否覆盖了全部 6 个分析维度（需求/能源/约束/区位/政策/稳定性）？分析是否有洞察？ |
| 建议合理性 | 替代省份建议是否合理？风险提示是否到位？ |
| 格式规范 | 报告结构是否完整（摘要/逐维分析/替代建议/风险/来源）？排版是否专业？ |
| 可操作性 | 读者能否根据报告做出选址决策？建议是否具体可执行？ |

## 输出格式（严格遵守）

```json
{
  "total_score": 7.5,
  "scores": {
    "数据准确性": 8,
    "分析深度": 7,
    "建议合理性": 8,
    "格式规范": 7,
    "可操作性": 7
  },
  "passed": false,
  "feedback": "整体分析框架完整，但需要加强以下方面: ...",
  "improvement_suggestions": [
    "补充目标省份与替代省份的定量对比表",
    "风险提示部分需要更具体的政策约束分析",
    "建议增加企划书数据与NAT_FINAL数据的对照表"
  ]
}
```

评分规则: total_score ≥ 8.0 并且每项 ≥ 6 才算通过。
如果未通过，feedback 和 improvement_suggestions 需要具体指出改进方向。
"""


@dataclass
class ReviewResult:
    total_score: float
    scores: dict[str, int]
    passed: bool
    feedback: str
    improvement_suggestions: list[str] = field(default_factory=list)
    raw_response: str = ""


class MiniMaxReviewer:
    """MiniMax 评审器

    用法:
        reviewer = MiniMaxReviewer()
        result = reviewer.review(report_text)
        if not result.passed:
            # 根据 feedback 修改报告，再次评审
            result = reviewer.review(revised_report_text)
    """

    def __init__(self):
        self._max_rounds = 5  # 最多评审 5 轮

    def review(self, report_text: str) -> ReviewResult:
        """评审一份报告，返回分数和修改建议"""
        import json as json_mod

        prompt = (
            f"{REVIEW_SYSTEM_PROMPT}\n\n"
            f"## 待评审报告\n\n{report_text[:8000]}\n\n"
            f"## 请评分"
        )

        # 这里通过 MCP 工具调用 MiniMax
        # 在 MCP server 中，我们会传入 minimax_chat 函数
        try:
            raw = self._call_minimax(prompt)
            # 提取 JSON
            json_str = raw
            if "```json" in raw:
                json_str = raw.split("```json")[1].split("```")[0]
            elif "```" in raw:
                json_str = raw.split("```")[1].split("```")[0]

            data = json_mod.loads(json_str.strip())
            return ReviewResult(
                total_score=float(data["total_score"]),
                scores=data.get("scores", {}),
                passed=data.get("passed", False),
                feedback=data.get("feedback", ""),
                improvement_suggestions=data.get("improvement_suggestions", []),
                raw_response=raw,
            )
        except Exception as e:
            return ReviewResult(
                total_score=0,
                scores={},
                passed=False,
                feedback=f"评审过程出错: {e}",
            )

    def set_minimax_fn(self, fn):
        """注入 MiniMax 调用函数（由 MCP tool handler 注入）"""
        self._call_minimax = fn

    def _call_minimax(self, prompt: str) -> str:
        """默认实现，需要在运行时注入"""
        raise NotImplementedError("请在运行时注入 MiniMax 调用函数")


def review_loop(
    reviewer: MiniMaxReviewer,
    generate_fn,
    proposal_text: str,
    target_province: str,
    max_rounds: int = 5,
) -> tuple[Path, ReviewResult, list[dict]]:
    """
    循环评审：生成 → 评审 → <8分就修改 → ≥8分输出

    Args:
        reviewer: MiniMaxReviewer 实例
        generate_fn: 报告生成函数 (feedback: str | None) -> (Path, str)
        proposal_text: 企划书文本
        target_province: 目标省份
        max_rounds: 最大轮次

    Returns:
        (最终PDF路径, 最终评审结果, 评审历史)
    """
    history = []
    feedback = None

    for round_num in range(1, max_rounds + 1):
        # 生成报告
        pdf_path, report_text = generate_fn(feedback)

        # 评审
        result = reviewer.review(report_text)
        history.append({
            "round": round_num,
            "score": result.total_score,
            "passed": result.passed,
            "feedback": result.feedback,
        })

        if result.passed:
            return pdf_path, result, history

        # 将反馈传给下一轮
        feedback = result.feedback

    # 达到最大轮次仍未通过，返回最后一版
    pdf_path, report_text = generate_fn(feedback)
    final_result = reviewer.review(report_text)
    return pdf_path, final_result, history
