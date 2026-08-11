"""省份诊断"""
import streamlit as st

st.title("🏙️ 省份诊断")
from src.dashboard.data_loader import get_query_engine, load_shared_data
from src.dashboard.components.charts import radar, trend_area
from src.core.exceptions import ProvinceNotFoundError


def show():
    qe = get_query_engine()
    data = load_shared_data(qe)

    province = st.selectbox("选择省份", data["provinces"], index=0)

    try:
        summary = qe.get_province_summary(province)
        dims = qe.get_dimension_scores(province, 2024)
        history = qe.get_score_history(province)

        c1, c2, c3 = st.columns(3)
        c1.metric("综合得分", f"{summary.composite_score:.4f}")
        c2.metric("全国排名", f"第 {summary.score_rank} 名")
        c3.metric("布局类型", summary.layout_type)
        c4, c5, c6 = st.columns(3)
        c4.metric("LPA 类型", summary.lpa_type_name or "-")
        c5.metric("稳定性", summary.stability_label)
        c6.metric("DC / 枢纽", f"DC×{summary.green_dc_count_2023} | {'枢纽' if summary.is_hub else '非枢纽'}")

        # 雷达 + 趋势：全宽各自渲染，不挤
        st.plotly_chart(radar(dims, f"🎯 {province} 七维画像"), use_container_width=True)
        st.plotly_chart(trend_area(history, province), use_container_width=True)

        if summary.lisa_type_2024 != "不显著":
            st.info(f"🗺️ **LISA**: {summary.lisa_type_2024}")

        if summary.stability_label == "边界型":
            st.warning(f"⚠️ {province} 属于**布局边界省份**，Bootstrap 保持率仅 {summary.keep_baseline_prob:.0%}。")

    except ProvinceNotFoundError:
        st.error(f"省份 '{province}' 不存在")

show()
