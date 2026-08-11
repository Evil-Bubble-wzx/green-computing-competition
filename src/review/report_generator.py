"""
企划书建议报告 PDF 生成器
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from datetime import datetime


@dataclass
class ReportSection:
    title: str
    content: str


def generate_pdf_report(
    proposal_name: str,
    target_province: str,
    sections: list[ReportSection],
    score: float | None = None,
    output_dir: str | Path = "./data/reports",
) -> Path:
    """
    生成企划书咨询建议 PDF 报告。

    Args:
        proposal_name: 企划书名称
        target_province: 目标省份
        sections: 报告各章节
        score: MiniMax 评审分数（如果有）
        output_dir: 输出目录

    Returns:
        生成的 PDF 文件路径
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{proposal_name}_{target_province}_{timestamp}.pdf"
    filepath = output_dir / filename

    # 优先用 fpdf2，不可用时用纯 Python 生成 HTML（浏览器可直接打印为 PDF）
    try:
        import fpdf2  # noqa: F401
        _write_with_fpdf(filepath, proposal_name, target_province, sections, score)
    except ImportError:
        try:
            _write_pure_pdf(filepath, proposal_name, target_province, sections, score)
        except Exception:
            html_path = output_dir / filename.replace(".pdf", ".html")
            _write_html(html_path, proposal_name, target_province, sections, score)
            return html_path

    return filepath


def _write_with_fpdf(filepath, proposal_name, target_province, sections, score):
    """用 fpdf2 生成 PDF"""
    from fpdf import FPDF

    pdf = FPDF()
    pdf.add_page()

    # 中文字体
    font_path = _find_chinese_font()
    if font_path:
        pdf.add_font("CJK", "", font_path, uni=True)
        pdf.add_font("CJK", "B", font_path, uni=True)
        body_font = "CJK"
    else:
        body_font = "Helvetica"

    def write_section(title, content, bold_title=True):
        if body_font == "CJK":
            pdf.set_font(body_font, "B" if bold_title else "", 14)
        else:
            pdf.set_font(body_font, "B" if bold_title else "", 12)
        pdf.cell(0, 10, title, ln=True)
        pdf.ln(2)
        if body_font == "CJK":
            pdf.set_font(body_font, "", 11)
        else:
            pdf.set_font(body_font, "", 10)
        # 简单分段
        for line in content.split("\n"):
            line = line.strip()
            if line:
                pdf.multi_cell(0, 6, line)
        pdf.ln(4)

    # 封面
    if body_font == "CJK":
        pdf.set_font(body_font, "B", 18)
    else:
        pdf.set_font(body_font, "B", 16)
    pdf.cell(0, 15, "省域绿色算力承载能力评估", ln=True, align="C")
    pdf.cell(0, 15, "企划书咨询建议报告", ln=True, align="C")
    pdf.ln(5)
    if body_font == "CJK":
        pdf.set_font(body_font, "", 12)
    else:
        pdf.set_font(body_font, "", 10)
    pdf.cell(0, 8, f"企划书: {proposal_name}", ln=True, align="C")
    pdf.cell(0, 8, f"目标省份: {target_province}", ln=True, align="C")
    pdf.cell(0, 8, f"生成日期: {datetime.now().strftime('%Y-%m-%d %H:%M')}", ln=True, align="C")
    pdf.cell(0, 8, f"数据版本: NAT_FINAL", ln=True, align="C")
    if score is not None:
        pdf.cell(0, 8, f"MiniMax 评审分数: {score}/10", ln=True, align="C")
    pdf.ln(10)

    # 各章节
    for sec in sections:
        write_section(sec.title, sec.content)

    # 页脚
    pdf.set_y(-20)
    pdf.set_font(body_font, "", 8)
    pdf.cell(0, 10, f"本报告由绿色算力智能决策助手自动生成 | 数据版本 NAT_FINAL | {datetime.now().strftime('%Y-%m-%d')}", align="C")

    pdf.output(str(filepath))


def _write_html(filepath, proposal_name, target_province, sections, score):
    """备选: 生成 HTML 报告"""
    sections_html = ""
    for sec in sections:
        sections_html += f"<h2>{sec.title}</h2>\n<p>{sec.content.replace(chr(10), '<br>')}</p>\n"

    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head><meta charset="utf-8"><title>企划书咨询建议报告 - {proposal_name}</title>
<style>
  body {{ font-family: 'PingFang SC', 'Microsoft YaHei', sans-serif; max-width: 800px; margin: 0 auto; padding: 40px; }}
  h1 {{ text-align: center; color: #2c3e50; }}
  .meta {{ text-align: center; color: #7f8c8d; font-size: 14px; margin-bottom: 30px; }}
  h2 {{ color: #2980b9; border-bottom: 2px solid #3498db; padding-bottom: 5px; }}
  p {{ line-height: 1.8; }}
  .footer {{ margin-top: 40px; padding-top: 10px; border-top: 1px solid #ddd; font-size: 12px; color: #999; text-align: center; }}
</style></head>
<body>
<h1>省域绿色算力承载能力评估<br>企划书咨询建议报告</h1>
<div class="meta">
  <p>企划书: {proposal_name} | 目标省份: {target_province}</p>
  <p>生成日期: {datetime.now().strftime('%Y-%m-%d %H:%M')} | 数据版本: NAT_FINAL</p>
  {f'<p>MiniMax 评审分数: {score}/10</p>' if score else ''}
</div>
{sections_html}
<div class="footer">本报告由绿色算力智能决策助手自动生成 | 仅供参考</div>
</body></html>"""

    filepath.write_text(html, encoding="utf-8")


def _write_pure_pdf(filepath, proposal_name, target_province, sections, score):
    """纯 Python 生成 PDF（无外部依赖）"""
    import zlib, struct, io

    # 构建文本内容
    lines = [
        f"企划书咨询建议报告",
        f"",
        f"企划书: {proposal_name}",
        f"目标省份: {target_province}",
        f"生成日期: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        f"数据版本: NAT_FINAL",
    ]
    if score is not None:
        lines.append(f"MiniMax 评审分数: {score}/10")
    lines.append("")
    for sec in sections:
        lines.append(f"{sec.title}")
        lines.append(sec.content)
        lines.append("")

    text = "\n".join(lines)

    # PDF 对象
    objects = []
    offsets = []

    def add_obj(data):
        offsets.append(None)  # placeholder
        objects.append(data)

    # Object 1: Catalog
    add_obj(b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n")
    # Object 2: Pages
    add_obj(b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n")
    # Object 3: Page
    add_obj(b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>\nendobj\n")

    # Object 4: Content stream
    content = text.encode("utf-8")
    compressed = zlib.compress(content)
    content_obj = (
        b"4 0 obj\n<< /Length " + str(len(compressed)).encode() +
        b" /Filter /FlateDecode >>\nstream\n" + compressed + b"\nendstream\nendobj\n"
    )
    add_obj(content_obj)

    # Object 5: Font (base font, no CJK - fallback)
    add_obj(b"5 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\nendobj\n")

    # 计算偏移量
    pos = 0
    # Header
    header = b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n"
    pos += len(header)

    for i, obj in enumerate(objects):
        offsets[i] = pos
        pos += len(obj)

    # Xref table
    xref = b"xref\n"
    xref += f"0 {len(objects) + 1}\n".encode()
    xref += f"0000000000 65535 f \n".encode()
    for off in offsets:
        xref += f"{off:010d} 00000 n \n".encode()

    # Trailer
    trailer = (
        b"trailer\n<< /Size " + str(len(objects) + 1).encode() +
        b" /Root 1 0 R >>\nstartxref\n" + str(pos).encode() + b"\n%%EOF"
    )

    with open(filepath, "wb") as f:
        f.write(header)
        for obj in objects:
            f.write(obj)
        f.write(xref)
        f.write(trailer)


def _find_chinese_font() -> str | None:
    """查找系统中可用的中文字体"""
    candidates = [
        "/System/Library/Fonts/PingFang.ttc",
        "/System/Library/Fonts/STHeiti Light.ttc",
        "/System/Library/Fonts/STHeiti Medium.ttc",
        "/Library/Fonts/Arial Unicode.ttf",
        "/System/Library/Fonts/Supplemental/Songti.ttc",
    ]
    for path in candidates:
        if Path(path).exists():
            return path
    return None
