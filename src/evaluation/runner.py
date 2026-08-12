"""
评估运行器 — 五维系统评估

H1: Golden Set 数据一致性 (H1-A 字段一致性 + H1-B LPA交叉验证)
H2: 问答质量 (关键词覆盖 + 术语合规)
H3: RAG 数字追溯 (整数+浮点数 DB 追溯 + 流式路径覆盖)
H4: 标准答案准确性 (LLM 输出 vs Golden Set)
H5: Dashboard-DB 一致性 (页面数据 vs 查询结果)
"""

from __future__ import annotations

import sys
import time
from datetime import datetime
from pathlib import Path

from src.core.settings import load_settings
from src.data.database import DatabaseManager
from src.data.queries import QueryEngine
from src.evaluation.golden_test import GoldenSetValidator
from src.evaluation.lpa_validator import LPAValidator
from src.evaluation.qa_quality import QAQualityEvaluator, TEST_QUESTIONS
from src.evaluation.rag_traceability import RAGTraceabilityEvaluator
from src.evaluation.qa_standard import QAStandardEvaluator
from src.evaluation.dashboard_consistency import DashboardConsistencyChecker
from src.evaluation.report import ReportGenerator


def run_all() -> int:
    start_all = time.time()
    print("═" * 70)
    print("  绿色算力智能决策助手 — 系统综合评估报告")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("═" * 70)

    settings = load_settings("config/settings.yaml")
    db = DatabaseManager(settings)
    qe = QueryEngine(db)

    # =====================================================================
    # 共享资源初始化 (LLM + ChatEngine, 一次创建供 H2/H3/H4 共用)
    # =====================================================================

    engine = None
    llm = None
    searcher = None

    try:
        from src.libs.llm.llm_factory import LLMFactory
        from src.retrieval.hybrid_search import HybridSearcher
        from src.chat.engine import ChatEngine

        llm = LLMFactory.create(settings)
        searcher = HybridSearcher(query_engine=qe)
        engine = ChatEngine(llm, searcher)
    except Exception as e:
        print(f"\n  ⚠️  LLM/ChatEngine 初始化失败: {e}")
        print(f"  H2/H3/H4 将跳过（仅运行 H1 + H5）\n")

    # =====================================================================
    # H1: Golden Set 数据一致性
    # =====================================================================
    print("\n" + "─" * 70)
    print("  H1  Golden Set 数据一致性")
    print("─" * 70)

    # H1-A: 字段一致性 (现有)
    print("\n  [H1-A] 13字段一致性...")
    validator = GoldenSetValidator(db, settings.data.docx_dir)
    r_h1a = validator.run_all()
    h1a_data = {
        "total_checks": r_h1a.total_checks,
        "passed": r_h1a.passed,
        "failed": r_h1a.failed,
        "pass_rate": r_h1a.passed / r_h1a.total_checks if r_h1a.total_checks > 0 else 1.0,
        "details": r_h1a.details,
        "errors": r_h1a.errors,
    }

    print(f"  ✅ 通过: {r_h1a.passed}/{r_h1a.total_checks}" if r_h1a.failed == 0
          else f"  ❌ 失败: {r_h1a.failed}/{r_h1a.total_checks}")
    if r_h1a.errors:
        for err in r_h1a.errors[:5]:
            print(f"     {err}")

    # H1-B: LPA 交叉验证 (新增)
    print("\n  [H1-B] LPA 交叉验证...")
    lpa_validator = LPAValidator(db, settings.data.docx_dir)
    r_h1b = lpa_validator.run_all()
    h1b_data = {
        "total_checks": r_h1b.total_checks,
        "passed": r_h1b.passed,
        "failed": r_h1b.failed,
        "pass_rate": r_h1b.passed / r_h1b.total_checks if r_h1b.total_checks > 0 else 1.0,
        "details": r_h1b.details,
        "errors": r_h1b.errors,
    }

    print(f"  ✅ 通过: {r_h1b.passed}/{r_h1b.total_checks}" if r_h1b.failed == 0
          else f"  ❌ 失败: {r_h1b.failed}/{r_h1b.total_checks}")
    if r_h1b.errors:
        for err in r_h1b.errors[:5]:
            print(f"     {err}")

    h1_ok = r_h1a.failed == 0 and r_h1b.failed == 0

    # =====================================================================
    # H2: 问答质量 (关键词 + 术语)
    # =====================================================================
    h2_data = None
    h2_ok = None
    if engine:
        print("\n" + "─" * 70)
        print("  H2  智能问答质量评估")
        print("─" * 70)

        try:
            evaluator = QAQualityEvaluator(engine)
            suite = evaluator.run_all()

            results_list = []
            for result in suite.results:
                icon = "✅" if result.passed else "❌"
                print(f"\n  {icon} {result.question_id}: {result.details}")

            h2_data = {
                "total": suite.total,
                "passed": suite.passed,
                "pass_rate": suite.pass_rate,
                "results": suite.results,
            }
            h2_ok = suite.passed >= 8
            print(f"\n  通过: {suite.passed}/{suite.total} ({suite.pass_rate:.0%})")

        except Exception as e:
            print(f"\n  ⚠️  H2 跳过: {e}")
            h2_ok = None

    # =====================================================================
    # H3: RAG 数字追溯
    # =====================================================================
    h3_data = None
    h3_ok = None
    if engine:
        print("\n" + "─" * 70)
        print("  H3  RAG 数字追溯")
        print("─" * 70)

        try:
            trace_eval = RAGTraceabilityEvaluator(qe, engine)
            trace_suite = trace_eval.run_all()

            for r in trace_suite.results:
                icon = "✅" if r.passed else "⚠️"
                print(f"  {icon} {r.question_id}: {r.traced_to_db}/{r.total_expected} 可追溯"
                      f" (率={r.trace_rate:.0%})")

            h3_data = {
                "total": trace_suite.total,
                "passed": trace_suite.passed,
                "pass_rate": trace_suite.passed / trace_suite.total if trace_suite.total else 1.0,
                "overall_trace_rate": trace_suite.overall_trace_rate,
                "results": trace_suite.results,
                "streaming_consistency": trace_suite.streaming_consistency,
            }

            print(f"\n  总追溯率: {trace_suite.overall_trace_rate:.1%}")
            h3_ok = trace_suite.overall_trace_rate >= 0.90

            # 流式一致性
            sc = trace_suite.streaming_consistency
            if sc:
                all_cons = all(v.get("consistent", True) for v in sc.values())
                print(f"  流式一致性: {'✅' if all_cons else '⚠️'}")

        except Exception as e:
            print(f"\n  ⚠️  H3 跳过: {e}")
            h3_ok = None

    # =====================================================================
    # H4: 标准答案准确性
    # =====================================================================
    h4_data = None
    h4_ok = None
    if engine:
        print("\n" + "─" * 70)
        print("  H4  标准答案准确性")
        print("─" * 70)

        try:
            std_eval = QAStandardEvaluator(qe, engine)
            std_suite = std_eval.run_all()

            for r in std_suite.results:
                icon = "✅" if r.passed else "❌"
                print(f"  {icon} {r.question_id}: {r.details}")
                if r.extracted_value:
                    print(f"     提取: {r.extracted_value}")
                    print(f"     期望: {r.expected_value}")

            h4_data = {
                "total": std_suite.total,
                "passed": std_suite.passed,
                "pass_rate": std_suite.pass_rate,
                "overall_accuracy": std_suite.overall_accuracy,
                "results": std_suite.results,
            }
            h4_ok = std_suite.passed >= 8
            print(f"\n  通过: {std_suite.passed}/{std_suite.total} ({std_suite.pass_rate:.0%})")

        except Exception as e:
            print(f"\n  ⚠️  H4 跳过: {e}")
            h4_ok = None

    # =====================================================================
    # H5: Dashboard-DB 一致性
    # =====================================================================
    print("\n" + "─" * 70)
    print("  H5  Dashboard-DB 一致性")
    print("─" * 70)

    try:
        dash_checker = DashboardConsistencyChecker(qe)
        dash_suite = dash_checker.run_all()

        for c in dash_suite.checks:
            icon = "✅" if c.passed else "❌"
            print(f"  {icon} [{c.page}] {c.check_name}: {c.detail}")

        h5_data = {
            "total": dash_suite.total,
            "passed": dash_suite.passed,
            "pass_rate": dash_suite.pass_rate,
            "checks": dash_suite.checks,
        }
        h5_ok = dash_suite.passed == dash_suite.total
        print(f"\n  通过: {dash_suite.passed}/{dash_suite.total} ({dash_suite.pass_rate:.0%})")

    except Exception as e:
        print(f"\n  ⚠️  H5 跳过: {e}")
        h5_data = None
        h5_ok = None

    # =====================================================================
    # 生成综合报告
    # =====================================================================
    elapsed = time.time() - start_all

    report = ReportGenerator.generate(
        h1_golden=h1a_data,
        h1_lpa=h1b_data,
        h2_qa_quality=h2_data,
        h3_traceability=h3_data,
        h4_standard=h4_data,
        h5_dashboard=h5_data,
        elapsed=elapsed,
    )

    # 打印格式化的总结报告
    ReportGenerator.print_console(report)

    # 保存 Markdown 报告
    report_dir = Path("data/reports")
    report_dir.mkdir(parents=True, exist_ok=True)
    report_path = report_dir / f"eval_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
    ReportGenerator.to_markdown(report, report_path)
    print(f"  📄 Markdown 报告已保存: {report_path}")
    print()

    db.close()
    return 0 if report.overall_pass else 1


if __name__ == "__main__":
    sys.exit(run_all())
