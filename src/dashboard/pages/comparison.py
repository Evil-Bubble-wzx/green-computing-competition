"""多省对比"""
import streamlit as st
from src.dashboard.data_loader import get_query_engine, load_shared_data
from src.dashboard.components.charts import multi_radar, multi_trend

qe = get_query_engine()
data = load_shared_data(qe)


selected = st.multiselect(
    "选择省份（最多 5 个）", data["provinces"],
    default=["江苏", "广东", "浙江"], max_selections=5,
)
if not selected:
    st.info("请选择至少 1 个省份")
    st.stop()

year = st.selectbox("年份", list(range(2016, 2025)), index=8)

st.subheader(f"📊 {year} 年对比")
rows, radar_data = [], []
for p in selected:
    try:
        s = qe.get_province_summary(p)
        dims = qe.get_dimension_scores(p, year)
        rows.append({"省份": p, "排名": f"#{s.score_rank}", "综合得分": f"{s.composite_score:.4f}",
                     "布局": s.layout_type, "LPA": s.lpa_type_name or "-", "稳定性": s.stability_label})
        radar_data.append((p, dims))
    except Exception:
        rows.append({"省份": p, "排名": "?", "综合得分": "?", "布局": "-", "LPA": "-", "稳定性": "-"})
st.dataframe(rows, use_container_width=True, hide_index=True)

# 雷达 + 趋势 上下排列（动态范围，不挤）
if radar_data:
    st.plotly_chart(multi_radar(radar_data), use_container_width=True)

trend_data = {}
for p in selected:
    try:
        h = qe.get_score_history(p)
        if h:
            trend_data[p] = [r["综合得分"] for r in h]
    except Exception:
        pass

if trend_data:
    years = [r["年份"] for r in qe.get_score_history(selected[0])]
    st.plotly_chart(multi_trend(trend_data, years), use_container_width=True)

