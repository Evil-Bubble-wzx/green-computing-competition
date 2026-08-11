"""空间分析"""
import streamlit as st
from src.dashboard.data_loader import get_query_engine, load_shared_data
from src.dashboard.components.charts import moran_chart, china_map

qe = get_query_engine()
data = load_shared_data(qe)

st.title("🗺️ 空间分析")

st.subheader("🌐 Global Moran's I")
moran = qe._all('SELECT * FROM "05_综合评价核心结果_NAT_FINAL_GlobalMoran_9999" ORDER BY "年份"')
if moran:
    st.plotly_chart(moran_chart(moran), use_container_width=True)
    sig = [f"{'★' if '5%' in str(r.get('显著性判断','')) else '☆'}{r['年份']}({r['Moran_I']:.3f})"
           for r in moran if "显著" in str(r.get("显著性判断", "")) and "不显著" not in str(r.get("显著性判断", ""))]
    st.caption("★ 5% 显著  ☆ 10% 边际  |  " + "  ".join(sig) if sig else "无显著年份")
else:
    st.info("暂无莫兰指数数据")

st.subheader("🇨🇳 省级空间分布")
m = china_map(data["ranking_2024"])
if m:
    st.plotly_chart(m, use_container_width=True)
    st.caption("注：台湾省、南沙群岛未做统计")
else:
    st.warning("GeoJSON 地图数据未找到")

st.subheader("📍 2024 LISA 局部空间分析")

lisa = data["lisa_sig"]
if lisa:
    st.dataframe(
        [{"省份": s["province"], "LISA 类型": s["lisa_type"], "综合得分": f"{s['score']:.4f}"} for s in lisa],
        use_container_width=True, hide_index=True,
    )
else:
    st.info("暂无显著 LISA 结果")

st.markdown("""
**LISA 类型说明**
- **HH (高-高)**: 自身高 + 邻域高 → 上海、江苏
- **HL (高-低)**: 自身高 + 邻域低 → 内蒙古、广东
- **LH (低-高)**: 自身低 + 邻域高 → 福建
- **LL (低-低)**: 自身低 + 邻域低 → 无

⚠️ 经 BH-FDR 多重比较校正 (q ≤ 0.10) 后所有省份均不显著，LISA 仅作探索性参考。
""")

with st.expander("📖 方法说明"):
    st.markdown("""
    - 空间权重矩阵: W0（省际邻接、行标准化、海南连广东广西）
    - 置换次数: 9999
    - LISA: 条件随机化（2024 年方法修复）
    - 多重检验: BH-FDR (q ≤ 0.10)
    """)

