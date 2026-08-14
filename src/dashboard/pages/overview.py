"""系统总览"""
import streamlit as st

from src.dashboard.data_loader import get_query_engine, load_shared_data
from src.dashboard.components.charts import ranking_lollipop, layout_sunburst, layout_bubble


def show():
    qe = get_query_engine()
    data = load_shared_data(qe)

    st.title("📊 系统总览")


    st.caption("31 省 × 2016–2024 × 7 维 34 指标")

    ranking = data["ranking_2024"]
    layout = data["layout_summary"]
    boundary = data["boundary"]

    # KPI
    top1 = ranking[0]
    high_suit = next((s for s in layout if "高适宜" in s["layout_type"]), None)
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("评估省份", "31")
    c2.metric("数据年份", "2016–2024")
    c3.metric("2024 第一", f"{top1['省份']} {top1['综合得分']:.3f}")
    c4.metric("高适宜承载区", f"{high_suit['count']} 省" if high_suit else "-")
    c5.metric("边界省份", f"{len(boundary)} 省")

    # 排名 + 布局
    left, right = st.columns([5, 3])
    with left:
        st.plotly_chart(ranking_lollipop(ranking, top_n=10), use_container_width=True)
    with right:
        st.plotly_chart(layout_sunburst(layout), use_container_width=True)

    # 布局详情表 + 气泡
    c1, c2 = st.columns([3, 2])
    with c1:
        st.subheader("📋 布局类型详情")
        rows = []
        for s in layout:
            provs = qe.get_provinces_by_layout(s["layout_type"])
            rows.append({
                "布局类型": s["layout_type"], "省份数": s["count"],
                "平均得分": f"{s['avg_score']:.4f}", "绿色DC": s["green_dc_total"],
                "枢纽": s["hub_count"],
                "省份": "、".join(provs),
            })
        st.dataframe(rows, use_container_width=True, hide_index=True, height=220)
    with c2:
        st.plotly_chart(layout_bubble(layout), use_container_width=True)

    if boundary:
        st.warning(
            "⚠️ **布局边界省份**: " +
            "、".join(f"{b['province']}({b['keep_prob']:.0%})" for b in boundary) +
            "\n\n这些省份布局不稳定，决策时需结合 LPA 和七维得分综合判断。"
        )

show()
