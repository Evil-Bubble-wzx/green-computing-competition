"""
统一评估报告生成器

收集 H1-H5 五项评估结果，生成终端输出和 Markdown 文件。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional


@dataclass
class EvaluationReport:
    """综合评估报告"""
    timestamp: str = ""
    h1_golden: Optional[dict] = None        # H1-A: Golden Set 字段一致性
    h1_lpa: Optional[dict] = None           # H1-B: LPA 交叉验证
    h2_qa_quality: Optional[dict] = None    # H2: 问答质量
    h3_traceability: Optional[dict] = None  # H3: RAG 数字追溯
    h4_standard: Optional[dict] = None      # H4: 标准答案准确性
    h5_dashboard: Optional[dict] = None     # H5: Dashboard-DB 一致性

    overall_pass: bool = False
    overall_score: float = 0.0              # 0-100
    elapsed_seconds: float = 0.0

    # 详细子项得分
    h1_score: float = 0.0
    h2_score: float = 0.0
    h3_score: float = 0.0
    h4_score: float = 0.0
    h5_score: float = 0.0


class ReportGenerator:
    """评估报告生成器

    用法:
        gen = ReportGenerator()
        report = gen.generate(h1, h1_lpa, h2, h3, h4, h5, elapsed)
        gen.print_console(report)
        gen.to_markdown(report, "reports/eval_20260812.md")
    """

    # 评分权重
    WEIGHTS = {
        "H1": 0.30,   # 数据一致性 (H1-A + H1-B)
        "H2": 0.15,   # 问答质量
        "H3": 0.25,   # RAG 数字追溯
        "H4": 0.15,   # 标准答案准确性
        "H5": 0.15,   # Dashboard 一致性
    }

    PASS_THRESHOLD = 85.0   # 综合评分通过线

    @staticmethod
    def generate(
        h1_golden: dict | None = None,
        h1_lpa: dict | None = None,
        h2_qa_quality: dict | None = None,
        h3_traceability: dict | None = None,
        h4_standard: dict | None = None,
        h5_dashboard: dict | None = None,
        elapsed: float = 0.0,
    ) -> EvaluationReport:
        report = EvaluationReport(
            timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            h1_golden=h1_golden,
            h1_lpa=h1_lpa,
            h2_qa_quality=h2_qa_quality,
            h3_traceability=h3_traceability,
            h4_standard=h4_standard,
            h5_dashboard=h5_dashboard,
            elapsed_seconds=elapsed,
        )

        # 计算各维度得分 (0-100)
        report.h1_score = ReportGenerator._score_h1(h1_golden, h1_lpa)
        report.h2_score = ReportGenerator._score_h2(h2_qa_quality)
        report.h3_score = ReportGenerator._score_h3(h3_traceability)
        report.h4_score = ReportGenerator._score_h4(h4_standard)
        report.h5_score = ReportGenerator._score_h5(h5_dashboard)

        # 加权综合评分
        report.overall_score = (
            report.h1_score * ReportGenerator.WEIGHTS["H1"]
            + report.h2_score * ReportGenerator.WEIGHTS["H2"]
            + report.h3_score * ReportGenerator.WEIGHTS["H3"]
            + report.h4_score * ReportGenerator.WEIGHTS["H4"]
            + report.h5_score * ReportGenerator.WEIGHTS["H5"]
        )

        report.overall_pass = report.overall_score >= ReportGenerator.PASS_THRESHOLD
        return report

    # ------------------------------------------------------------------
    # 各维度评分函数
    # ------------------------------------------------------------------

    @staticmethod
    def _score_h1(golden: dict | None, lpa: dict | None) -> float:
        if golden is None:
            return 0.0
        # H1-A: Golden 字段 (权重 0.7), H1-B: LPA (权重 0.3)
        golden_rate = golden.get("pass_rate", 1.0) if isinstance(golden, dict) else 1.0
        lpa_rate = lpa.get("pass_rate", 1.0) if isinstance(lpa, dict) else 1.0
        return (golden_rate * 0.7 + lpa_rate * 0.3) * 100

    @staticmethod
    def _score_h2(qa: dict | None) -> float:
        if qa is None:
            return 0.0
        pass_rate = qa.get("pass_rate", 0.0) if isinstance(qa, dict) else 0.0
        return pass_rate * 100

    @staticmethod
    def _score_h3(trace: dict | None) -> float:
        if trace is None:
            return 0.0
        rate = trace.get("overall_trace_rate", 0.0) if isinstance(trace, dict) else 0.0
        return rate * 100

    @staticmethod
    def _score_h4(std: dict | None) -> float:
        if std is None:
            return 0.0
        rate = std.get("pass_rate", 0.0) if isinstance(std, dict) else 0.0
        return rate * 100

    @staticmethod
    def _score_h5(dash: dict | None) -> float:
        if dash is None:
            return 0.0
        rate = dash.get("pass_rate", 0.0) if isinstance(dash, dict) else 0.0
        return rate * 100

    # ------------------------------------------------------------------
    # 终端输出
    # ------------------------------------------------------------------

    @staticmethod
    def print_console(report: EvaluationReport):
        """打印彩色终端报告"""
        print()
        print("═" * 70)
        print("  绿色算力智能决策助手 — 系统综合评估报告")
        print(f"  {report.timestamp}")
        print("═" * 70)

        # --- H1 ---
        print()
        print("─" * 70)
        print("  H1  Golden Set 数据一致性")
        print("─" * 70)
        ReportGenerator._print_h1_sub(report)

        # --- H2 ---
        print()
        print("─" * 70)
        print("  H2  问答质量 (关键词 + 术语)")
        print("─" * 70)
        ReportGenerator._print_h2(report)

        # --- H3 ---
        print()
        print("─" * 70)
        print("  H3  RAG 数字追溯")
        print("─" * 70)
        ReportGenerator._print_h3(report)

        # --- H4 ---
        print()
        print("─" * 70)
        print("  H4  标准答案准确性")
        print("─" * 70)
        ReportGenerator._print_h4(report)

        # --- H5 ---
        print()
        print("─" * 70)
        print("  H5  Dashboard-DB 一致性")
        print("─" * 70)
        ReportGenerator._print_h5(report)

        # --- 总结 ---
        print()
        print("═" * 70)
        print("  评估总结")
        print("═" * 70)

        h1_ok = report.h1_score >= 95
        h2_ok = report.h2_score >= 80
        h3_ok = report.h3_score >= 90
        h4_ok = report.h4_score >= 80
        h5_ok = report.h5_score >= 95

        def status(passed: bool) -> str:
            return "✅ 通过" if passed else "⚠️ 待改进"

        print(f"  H1  数据一致性      {status(h1_ok)}   ({report.h1_score:.0f}/100)")
        print(f"  H2  问答质量        {status(h2_ok)}   ({report.h2_score:.0f}/100)")
        print(f"  H3  RAG数字追溯     {status(h3_ok)}   ({report.h3_score:.0f}/100)")
        print(f"  H4  标准答案准确性  {status(h4_ok)}   ({report.h4_score:.0f}/100)")
        print(f"  H5  Dashboard一致性 {status(h5_ok)}   ({report.h5_score:.0f}/100)")

        print()
        print(f"  综合评分: {report.overall_score:.0f}/100")
        print(f"  总耗时: {report.elapsed_seconds:.1f}s")

        if report.overall_pass:
            print(f"  结论: 🎉 系统可交付 — 全部评估通过")
        else:
            remaining = []
            if not h1_ok: remaining.append("H1")
            if not h2_ok: remaining.append("H2")
            if not h3_ok: remaining.append("H3")
            if not h4_ok: remaining.append("H4")
            if not h5_ok: remaining.append("H5")
            print(f"  结论: 🔧 需改进 ({', '.join(remaining)})")

        print("═" * 70)
        print()

    @staticmethod
    def _print_h1_sub(report: EvaluationReport):
        if report.h1_golden:
            g = report.h1_golden
            passed = g.get("passed", 0)
            total = g.get("total_checks", 0)
            failed = g.get("failed", 0)
            icon = "✅" if failed == 0 else "❌"
            print(f"  H1-A  13字段一致性     {icon}  ({passed}/{total})")
            if failed and g.get("details"):
                for d in g["details"][:5]:
                    print(f"         {d.get('province','')}.{d.get('field','')}: Excel={d.get('excel','')} DB={d.get('database','')}")

        if report.h1_lpa:
            lp = report.h1_lpa
            passed = lp.get("passed", 0)
            total = lp.get("total_checks", 0)
            failed = lp.get("failed", 0)
            h1b_icon = "✅" if failed == 0 else "❌"
            print(f"  H1-B  LPA交叉验证      {h1b_icon}  ({passed}/{total})")
            if failed and lp.get("errors"):
                for e in lp["errors"][:5]:
                    print(f"         {e}")

        if report.h1_golden and report.h1_lpa:
            total_all = report.h1_golden.get("total_checks", 0) + report.h1_lpa.get("total_checks", 0)
            passed_all = report.h1_golden.get("passed", 0) + report.h1_lpa.get("passed", 0)
            print(f"  小计: {passed_all}/{total_all} 项检查通过")

    @staticmethod
    def _print_h2(report: EvaluationReport):
        if not report.h2_qa_quality:
            print("  ⊘ 未运行")
            return
        h2 = report.h2_qa_quality
        results = h2.get("results", [])
        for r in results:
            icon = "✅" if r.passed else "❌"
            print(f"  {icon} {r.question_id}: {r.details}")
        print(f"  通过: {h2.get('passed',0)}/{h2.get('total',0)} ({h2.get('pass_rate',0):.0%})")

    @staticmethod
    def _print_h3(report: EvaluationReport):
        if not report.h3_traceability:
            print("  ⊘ 未运行")
            return
        h3 = report.h3_traceability
        for r in h3.get("results", []):
            icon = "✅" if r.passed else "⚠️"
            print(f"  {icon} {r.question_id}: {r.traced_to_db}/{r.total_expected} 追溯 (率={r.trace_rate:.0%})")
            for d in r.details:
                mark = "✓" if d.get("traced_to_db") else "✗"
                print(f"      {mark} {d.get('label', '')}")
        print(f"  总追溯率: {h3.get('overall_trace_rate', 0):.1%}")

        # 流式一致性
        sc = h3.get("streaming_consistency", {})
        if sc:
            all_consistent = all(v.get("consistent", True) for v in sc.values())
            icon = "✅" if all_consistent else "⚠️"
            print(f"  {icon} 流式一致性: {'全部一致' if all_consistent else '存在差异'}")

    @staticmethod
    def _print_h4(report: EvaluationReport):
        if not report.h4_standard:
            print("  ⊘ 未运行")
            return
        h4 = report.h4_standard
        for r in h4.get("results", []):
            icon = "✅" if r.passed else "❌"
            print(f"  {icon} {r.question_id}: {r.details}")
            if r.extracted_value:
                print(f"     提取值: {r.extracted_value}")
                print(f"     期望值: {r.expected_value}")
        print(f"  通过: {h4.get('passed',0)}/{h4.get('total',0)} ({h4.get('pass_rate',0):.0%})")

    @staticmethod
    def _print_h5(report: EvaluationReport):
        if not report.h5_dashboard:
            print("  ⊘ 未运行")
            return
        h5 = report.h5_dashboard
        for c in h5.get("checks", []):
            icon = "✅" if c.passed else "❌"
            print(f"  {icon} [{c.page}] {c.check_name}: {c.detail}")
        print(f"  通过: {h5.get('passed',0)}/{h5.get('total',0)} ({h5.get('pass_rate',0):.0%})")

    # ------------------------------------------------------------------
    # Markdown 导出
    # ------------------------------------------------------------------

    @staticmethod
    def to_markdown(report: EvaluationReport, path: str | Path | None = None) -> str:
        """生成 Markdown 报告，可选保存到文件"""
        lines = []
        lines.append("# 绿色算力智能决策助手 — 系统综合评估报告")
        lines.append(f"**评估时间**: {report.timestamp}")
        lines.append(f"**总耗时**: {report.elapsed_seconds:.1f}s")
        lines.append("")

        # H1
        lines.append("## H1 Golden Set 数据一致性")
        if report.h1_golden:
            g = report.h1_golden
            lines.append(f"- H1-A 13字段: {g.get('passed',0)}/{g.get('total_checks',0)}")
        if report.h1_lpa:
            lp = report.h1_lpa
            lines.append(f"- H1-B LPA交叉: {lp.get('passed',0)}/{lp.get('total_checks',0)}")
        lines.append("")

        # H2
        lines.append("## H2 问答质量")
        if report.h2_qa_quality:
            h2 = report.h2_qa_quality
            lines.append(f"- 通过: {h2.get('passed',0)}/{h2.get('total',0)}")
            lines.append("")
            for r in h2.get("results", []):
                lines.append(f"- {'✅' if r.passed else '❌'} {r.question_id}: {r.details}")
        lines.append("")

        # H3
        lines.append("## H3 RAG 数字追溯")
        if report.h3_traceability:
            h3 = report.h3_traceability
            lines.append(f"- 追溯率: {h3.get('overall_trace_rate',0):.1%}")
            for r in h3.get("results", []):
                lines.append(f"- {r.question_id}: {r.traced_to_db}/{r.total_expected} ({r.trace_rate:.0%})")
        lines.append("")

        # H4
        lines.append("## H4 标准答案准确性")
        if report.h4_standard:
            h4 = report.h4_standard
            lines.append(f"- 通过: {h4.get('passed',0)}/{h4.get('total',0)}")
            for r in h4.get("results", []):
                lines.append(f"- {'✅' if r.passed else '❌'} {r.question_id}: {r.details}")
        lines.append("")

        # H5
        lines.append("## H5 Dashboard-DB 一致性")
        if report.h5_dashboard:
            h5 = report.h5_dashboard
            lines.append(f"- 通过: {h5.get('passed',0)}/{h5.get('total',0)}")
            for c in h5.get("checks", []):
                lines.append(f"- {'✅' if c.passed else '❌'} [{c.page}] {c.check_name}: {c.detail}")
        lines.append("")

        # 总结
        lines.append("## 综合评估")
        lines.append(f"| 维度 | 得分 | 状态 |")
        lines.append(f"|------|------|------|")
        for name, score in [("H1 数据一致性", report.h1_score), ("H2 问答质量", report.h2_score),
                            ("H3 RAG追溯", report.h3_score), ("H4 标准答案", report.h4_score),
                            ("H5 Dashboard", report.h5_score)]:
            status = "✅" if score >= 80 else "⚠️"
            lines.append(f"| {name} | {score:.0f}/100 | {status} |")
        lines.append("")
        lines.append(f"**综合评分**: {report.overall_score:.0f}/100")
        lines.append(f"**结论**: {'🎉 可交付' if report.overall_pass else '🔧 需改进'}")

        md_content = "\n".join(lines)

        if path:
            Path(path).parent.mkdir(parents=True, exist_ok=True)
            Path(path).write_text(md_content, encoding="utf-8")

        return md_content
