"""布局决策"""
import streamlit as st

from src.dashboard.data_loader import get_query_engine, load_shared_data
from src.dashboard.components.charts import LAYOUT_COLORS

qe = get_query_engine()
data = load_shared_data(qe)

st.title("📐 布局决策")

layout = data["layout_summary"]
boundary = data["boundary"]

st.subheader("🏗️ V2A 五类布局")
if layout:
    cols = st.columns(len(layout))
    for i, s in enumerate(layout):
        color = LAYOUT_COLORS.get(s["layout_type"], "#94A3B8")
        with cols[i]:
            st.markdown(f"""
            <div style="background:{color};padding:16px 12px;border-radius:12px;color:white;text-align:center">
                <div style="font-size:12px;opacity:0.85;margin-bottom:6px">{s['layout_type']}</div>
                <div style="font-size:28px;font-weight:700">{s['count']}</div>
                <div style="font-size:11px;opacity:0.8;margin-top:4px">均分{s['avg_score']:.3f} | DC×{s['green_dc_total']}</div>
            </div>
            """, unsafe_allow_html=True)

st.subheader("📋 分类详情")
lt = st.selectbox("选择布局类型", [s["layout_type"] for s in layout])
provs = qe.get_provinces_by_layout(lt)
st.write(f"**{lt}**: {len(provs)} 省 — {'、'.join(provs)}")

rows = []
for p in provs:
    try:
        s = qe.get_province_summary(p)
        rows.append({"省份": p, "综合得分": f"{s.composite_score:.4f}", "排名": s.score_rank,
                     "LPA": s.lpa_type_name or "-", "稳定性": s.stability_label,
                     "绿色DC": s.green_dc_count_2023, "枢纽": "✓" if s.is_hub else ""})
    except Exception:
        pass
if rows:
    st.dataframe(rows, use_container_width=True, hide_index=True)

st.subheader("⚠️ 布局边界省份")
if boundary:
    st.dataframe(
        [{"省份": b["province"], "布局类型": b["layout_type"], "保持率": f"{b['keep_prob']:.1%}"} for b in boundary],
        use_container_width=True, hide_index=True,
    )
    st.caption("边界省份 Bootstrap 保持率 < 80%，选址建议需更谨慎。")

with st.expander("📖 V2A 布局规则"):
    st.markdown("""
    | 顺序 | 条件 | 类型 |
    |------|------|------|
    | 1 | 适宜度排名 ≤ 5 | 高适宜综合承载区 |
    | 2 | 适宜度排名 ≥ 28 | 约束控制区 |
    | 3 | 能源-需求 ≥ 0.18 | 能源低碳优势承接区 |
    | 4 | 需求 ≥ 0.33 且 能源-需求 < 0.10 | 需求网络驱动区 |
    | 5 | 其余 | 综合潜力提升区 |
    """)

