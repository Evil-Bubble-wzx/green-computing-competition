"""
评估运行器
"""

from __future__ import annotations

import sys, time
from datetime import datetime
from pathlib import Path

from src.core.settings import load_settings
from src.data.database import DatabaseManager
from src.data.queries import QueryEngine
from src.evaluation.golden_test import GoldenSetValidator
from src.evaluation.qa_quality import QAQualityEvaluator, TEST_QUESTIONS


def run_all() -> int:
    start_all = time.time()
    print("═" * 65)
    print("  绿色算力智能决策助手 — 系统评估报告")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("═" * 65)

    settings = load_settings("config/settings.yaml")
    db = DatabaseManager(settings)
    qe = QueryEngine(db)

    # =====================================================================
    # H1: Golden Set
    # =====================================================================
    print("\n" + "─" * 65)
    print("  H1  Golden Set 数据一致性")
    print("─" * 65)

    validator = GoldenSetValidator(db, settings.data.docx_dir)
    r = validator.run_all()

    print(f"  检查项: {r.total_checks}")
    print(f"  ✅ 通过: {r.passed}")
    if r.failed:
        print(f"  ❌ 失败: {r.failed}")
        for d in r.details[:20]:
            print(f"     {d['province']}.{d['field']}: Excel={d['excel']} DB={d['database']}")
    else:
        print(f"  结论: 所有字段与 Golden Set 完全一致 ✅")
    h1_ok = r.failed == 0

    # =====================================================================
    # H2: 问答质量
    # =====================================================================
    print("\n" + "─" * 65)
    print("  H2  智能问答质量评估 (DeepSeek v4 Flash)")
    print("─" * 65)

    try:
        from src.libs.llm.llm_factory import LLMFactory
        from src.retrieval.hybrid_search import HybridSearcher
        from src.chat.engine import ChatEngine

        llm = LLMFactory.create(settings)
        searcher = HybridSearcher(query_engine=qe)
        engine = ChatEngine(llm, searcher)
        evaluator = QAQualityEvaluator(engine)

        # 存答案以便展示
        answers = {}
        suite = evaluator.run_all()

        for i, tq in enumerate(TEST_QUESTIONS):
            qid = tq["id"]
            try:
                resp = engine.chat(tq["question"], mode=tq.get("mode", "data_query"))
                answers[qid] = resp.answer
            except Exception as e:
                answers[qid] = f"[错误] {e}"

            result = suite.results[i] if i < len(suite.results) else None
            if result is None:
                continue

            status = "✅" if result.passed else "❌"
            print(f"\n  {status} {qid}: {tq['question']}")
            print(f"     回答: {answers[qid][:120]}...")
            if not result.passed:
                print(f"     原因: {result.details}")

        h2_ok = suite.passed >= 8

        # 汇总
        print(f"\n  ─────────────────────")
        print(f"  通过: {suite.passed}/{suite.total}  ({suite.pass_rate:.0%})")
        accuracy = sum(1 for r in suite.results if r.accuracy)
        terminol = sum(1 for r in suite.results if r.terminology)
        rej = sum(1 for r in suite.results if r.rejection)
        print(f"  数值准确: {accuracy}/10 | 术语合规: {terminol}/10")
        print(f"  越界拒绝: {Q6_correct}/{1}" if (Q6_correct := sum(1 for r in suite.results if r.question_id == "Q6" and r.passed)) else f"  越界拒绝: {sum(1 for r in suite.results if r.rejection)}/{sum(1 for t in TEST_QUESTIONS if t.get('should_reject'))}")

    except Exception as e:
        print(f"\n  ⚠️  H2 跳过: {e}")
        h2_ok = None

    # =====================================================================
    # H3: 性能
    # =====================================================================
    print("\n" + "─" * 65)
    print("  H3  性能基准")
    print("─" * 65)

    n = 100
    start = time.time()
    for _ in range(n):
        qe.get_province_summary("江苏")
    db_ms = (time.time() - start) / n * 1000
    db_ok = db_ms < 5
    print(f"  {'✅' if db_ok else '⚠️'}  省份摘要查询: {db_ms:.1f}ms/次 ({n}次平均)")

    start = time.time()
    for _ in range(n):
        qe.list_all_provinces()
    list_ms = (time.time() - start) / n * 1000
    list_ok = list_ms < 5
    print(f"  {'✅' if list_ok else '⚠️'}  列表查询: {list_ms:.1f}ms/次")

    start = time.time()
    for _ in range(n):
        qe.get_dimension_scores("江苏", 2024)
    dim_ms = (time.time() - start) / n * 1000
    print(f"  {'✅' if dim_ms < 5 else '⚠️'}  维度查询: {dim_ms:.1f}ms/次")

    start = time.time()
    for _ in range(min(n, 10)):
        qe.get_layout_summary()
    layout_ms = (time.time() - start) / min(n, 10) * 1000
    print(f"  {'✅' if layout_ms < 10 else '⚠️'}  布局汇总: {layout_ms:.1f}ms/次")

    h3_ok = db_ok and list_ok

    # =====================================================================
    # 最终得分
    # =====================================================================
    elapsed = time.time() - start_all
    print("\n" + "═" * 65)
    print(f"  评估总结")
    print("═" * 65)

    lines = []
    lines.append(f"  H1 数据一致性     {'✅ 通过' if h1_ok else '❌ 失败'}     (Golden Set 403项)")
    if h2_ok is True:
        lines.append(f"  H2 问答质量       ✅ 通过     ({suite.passed}/10)")
    elif h2_ok is False:
        lines.append(f"  H2 问答质量       ⚠️ 待改进   ({suite.passed}/10)")
    else:
        lines.append(f"  H2 问答质量       ⊘ 未运行")
    lines.append(f"  H3 性能基准       {'✅ 通过' if h3_ok else '⚠️ 待改进'}     (查询 {db_ms:.1f}ms)")

    for line in lines:
        print(line)

    all_ok = h1_ok and (h2_ok is True) and h3_ok
    print(f"\n  总耗时: {elapsed:.1f}s")
    if all_ok:
        print(f"  结论: 🎉 系统可交付 — 全部评估通过")
    else:
        remaining = []
        if not h1_ok: remaining.append("H1")
        if h2_ok is not True: remaining.append("H2")
        if not h3_ok: remaining.append("H3")
        print(f"  结论: 🔧 需改进 ({', '.join(remaining)})")
    print("═" * 65)

    db.close()
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(run_all())
