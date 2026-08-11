"""
Proposal Review MCP 工具集
"""

import asyncio, json
from pathlib import Path


def register_all(handler, pipeline, chat_engine, reviewer, settings):
    if not all([chat_engine, reviewer]):
        return

    # ------------------------------------------------------------------
    # 1. generate_report — 分析企划书，生成 PDF 报告
    # ------------------------------------------------------------------
    async def generate_report(proposal_file: str, target_province: str):
        """分析企划书并生成 PDF 建议报告"""
        from src.review.report_generator import generate_pdf_report, ReportSection

        # 1) 把 PDF 文本取出来（如果已摄入则在 ChromaDB 中，否则直接解析）
        proposal_text = ""
        proposal_name = Path(proposal_file).stem
        try:
            from src.ingestion.pdf_parser import PDFParser
            doc = PDFParser().parse(proposal_file)
            proposal_text = doc.full_text[:8000]
        except Exception:
            proposal_text = f"企划书文件: {proposal_file}（未能自动解析，请确认文件存在）"

        # 2) 用 ChatEngine 分析
        query = (
            f"请分析以下企划书，目标省份是{target_province}。\n\n"
            f"企划书内容:\n{proposal_text}\n\n"
            f"请按照企划书分析框架逐维分析并给出建议。"
        )
        resp = await asyncio.to_thread(chat_engine.chat, query, None, "proposal_consult")

        # 3) 构建报告章节
        sections = [
            ReportSection("一、企划书分析", resp.answer),
            ReportSection("二、数据来源", "NAT_FINAL 数据版本，2024 年，31省省级评估"),
        ]
        if resp.evidence:
            evidence_text = "\n".join(
                f"- [{e.get('source', '?')}] {e.get('title', '')}: {e.get('snippet', '')[:200]}"
                for e in resp.evidence[:5]
            )
            sections.append(ReportSection("三、检索依据", evidence_text))

        # 4) 生成 PDF
        pdf_path = await asyncio.to_thread(
            generate_pdf_report,
            proposal_name, target_province, sections,
            output_dir=settings.data.get("report_dir", "./data/reports") if hasattr(settings.data, "get") else "./data/reports",
        )

        return json.dumps({
            "status": "success",
            "pdf_path": str(pdf_path),
            "proposal_name": proposal_name,
            "target_province": target_province,
            "answer_preview": resp.answer[:300],
        }, ensure_ascii=False)

    handler.register_tool(
        "generate_report",
        "分析企划书并生成 PDF 建议报告（包含逐维分析、替代建议、风险提示）",
        {
            "type": "object",
            "properties": {
                "proposal_file": {"type": "string", "description": "企划书 PDF 文件路径"},
                "target_province": {"type": "string", "description": "目标省份，如'贵州'"},
            },
            "required": ["proposal_file", "target_province"],
        },
        generate_report,
    )

    # ------------------------------------------------------------------
    # 2. review_report — MiniMax 评审报告
    # ------------------------------------------------------------------
    async def review_report(pdf_path: str):
        """用 MiniMax 评审已生成的报告"""
        # 读取报告内容
        report_text = ""
        p = Path(pdf_path)
        if p.suffix == ".html":
            report_text = p.read_text(encoding="utf-8")[:8000]
        elif p.suffix == ".pdf":
            try:
                from src.ingestion.pdf_parser import PDFParser
                doc = PDFParser().parse(pdf_path)
                report_text = doc.full_text[:8000]
            except Exception:
                report_text = f"PDF 文件: {pdf_path}（未能解析文本内容）"
        else:
            report_text = p.read_text(encoding="utf-8")[:8000]

        result = await asyncio.to_thread(reviewer.review, report_text)

        return json.dumps({
            "total_score": result.total_score,
            "scores": result.scores,
            "passed": result.passed,
            "feedback": result.feedback,
            "improvement_suggestions": result.improvement_suggestions,
        }, ensure_ascii=False)

    handler.register_tool(
        "review_report",
        "用 MiniMax-M3 评审企划书建议报告，按 5 个维度打分（满分 10）",
        {
            "type": "object",
            "properties": {
                "pdf_path": {"type": "string", "description": "PDF 报告文件路径"},
            },
            "required": ["pdf_path"],
        },
        review_report,
    )

    # ------------------------------------------------------------------
    # 3. auto_revise — 循环评审直到 ≥ 8 分
    # ------------------------------------------------------------------
    async def auto_revise(proposal_file: str, target_province: str):
        """自动循环：生成报告 → MiniMax 评审 → 修改 → 直到 ≥ 8 分"""
        from src.review.minimax_reviewer import review_loop
        from src.review.report_generator import generate_pdf_report, ReportSection
        from src.ingestion.pdf_parser import PDFParser

        proposal_name = Path(proposal_file).stem

        # 解析企划书
        try:
            doc = PDFParser().parse(proposal_file)
            proposal_text = doc.full_text[:8000]
        except Exception as e:
            return json.dumps({"status": "failed", "error": f"无法解析企划书: {e}"}, ensure_ascii=False)

        def generate_fn(feedback=None):
            """生成报告的函数"""
            extra = ""
            if feedback:
                extra = f"\n\n## 上一轮评审反馈（请据此改进）\n{feedback}"

            query = (
                f"请分析以下企划书，目标省份是{target_province}。\n\n"
                f"企划书内容:\n{proposal_text}\n{extra}"
            )
            resp = chat_engine.chat(query, mode="proposal_consult")

            sections = [
                ReportSection("一、企划书分析与建议", resp.answer),
                ReportSection("二、数据来源", "NAT_FINAL 数据版本，2024 年"),
            ]
            pdf_path = generate_pdf_report(proposal_name, target_province, sections)
            return pdf_path, resp.answer

        pdf_path, final_result, history = await asyncio.to_thread(
            review_loop, reviewer, generate_fn, proposal_text, target_province
        )

        return json.dumps({
            "status": "success" if final_result.passed else "max_rounds_reached",
            "pdf_path": str(pdf_path),
            "final_score": final_result.total_score,
            "passed": final_result.passed,
            "rounds": len(history),
            "history": history,
        }, ensure_ascii=False)

    handler.register_tool(
        "auto_revise",
        "自动循环：生成企划书报告 → MiniMax 评审 → 修改 → 直到评分 ≥ 8 分后输出",
        {
            "type": "object",
            "properties": {
                "proposal_file": {"type": "string", "description": "企划书 PDF 文件路径"},
                "target_province": {"type": "string", "description": "目标省份"},
            },
            "required": ["proposal_file", "target_province"],
        },
        auto_revise,
    )
