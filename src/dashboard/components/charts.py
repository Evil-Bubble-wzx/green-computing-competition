"""Dashboard 图表组件 — Plotly"""

import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import json
from pathlib import Path

# ── 色板 ──
PRIMARY = "#1E40AF"
ACCENT = "#D97706"
GREEN = "#059669"
FG = "#1E3A8A"
MUTED = "#94A3B8"
BORDER = "#DBEAFE"

LAYOUT_COLORS = {
    "高适宜综合承载区": "#3B7A9E",
    "需求网络驱动区": "#B07B8F",
    "能源低碳优势承接区": "#D4953A",
    "综合潜力提升区": "#C76A4A",
    "约束控制区": "#7B8D9B",
}

DIM_COLORS = ["#1E40AF", "#2563EB", "#3B82F6", "#059669", "#10B981", "#D97706", "#C76A4A"]
DIM_NAMES = ["算力需求基础", "数字基础设施", "能源供给能力", "绿色低碳约束", "气候与自然条件", "创新与人才支撑", "区域协同能力"]

LAYOUT_BASE = {
    "font": {"family": "Inter, sans-serif", "color": FG},
    "paper_bgcolor": "rgba(0,0,0,0)",
    "plot_bgcolor": "rgba(0,0,0,0)",
}

GEOJSON_PATH = Path(__file__).resolve().parent.parent.parent.parent / "data" / "china_provinces.geojson"

# ──────────────────────────────────────────────
# 1. 排名棒棒糖图
# ──────────────────────────────────────────────
def ranking_lollipop(ranking: list[dict], top_n: int = 15) -> go.Figure:
    df = pd.DataFrame(ranking[:top_n])
    df = df.iloc[::-1]  # 倒序让第一在上面

    fig = go.Figure()
    # 棒
    fig.add_trace(go.Scatter(
        x=df["综合得分"], y=df["省份"], mode="markers",
        marker={"size": 14, "color": PRIMARY, "line": {"width": 2, "color": "white"}},
        hovertemplate="<b>%{y}</b>: %{x:.4f}<extra></extra>",
    ))
    # 线
    for _, row in df.iterrows():
        fig.add_shape(type="line", x0=0, x1=row["综合得分"], y0=row["省份"], y1=row["省份"],
                      line={"color": BORDER, "width": 2})

    fig.update_layout(**LAYOUT_BASE, height=max(400, top_n * 26),
                      xaxis_title="综合得分", yaxis_title=None,
                      xaxis={"gridcolor": "#E2E8F0", "zeroline": False},
                      margin={"l": 10, "r": 40, "t": 50, "b": 20},
                      title={"text": "🏆 2024 年综合得分排名", "font": {"size": 16, "color": FG}})
    return fig


# ──────────────────────────────────────────────
# 2. 布局旭日图
# ──────────────────────────────────────────────
def layout_sunburst(layout: list[dict]) -> go.Figure:
    fig = go.Figure(go.Sunburst(
        labels=["31 省"] + [s["layout_type"] for s in layout],
        parents=[""] + ["31 省"] * len(layout),
        values=[sum(s["count"] for s in layout)] + [s["count"] for s in layout],
        marker={"colors": ["#F8FAFC"] + [LAYOUT_COLORS.get(s["layout_type"], MUTED) for s in layout]},
        textinfo="label+value",
        hovertemplate="<b>%{label}</b>: %{value} 省<extra></extra>",
    ))
    fig.update_layout(**LAYOUT_BASE, height=340,
                      title={"text": "🗂️ 布局分布", "font": {"size": 16, "color": FG}},
                      margin={"l": 0, "r": 0, "t": 50, "b": 0})
    return fig


# ──────────────────────────────────────────────
# 3. 雷达图
# ──────────────────────────────────────────────
def radar(dims: dict, title: str) -> go.Figure:
    values = [dims.get(k, 0) for k in DIM_NAMES]
    values.append(values[0])
    labels = DIM_NAMES + [DIM_NAMES[0]]

    # 动态范围：最大值恰好接触外圈
    max_v = max(v for v in values if v > 0) if any(v > 0 for v in values) else 0.5
    r_max = max_v

    fig = go.Figure(go.Scatterpolar(
        r=values, theta=labels, fill="toself",
        fillcolor="rgba(30,64,175,0.1)", line={"color": PRIMARY, "width": 2},
        name=title,
    ))
    fig.update_layout(**LAYOUT_BASE, height=480, polar={
        "radialaxis": {"visible": True, "gridcolor": "#E2E8F0", "range": [0, r_max]},
        "angularaxis": {"gridcolor": "#E2E8F0"},
    }, title={"text": title, "font": {"size": 14, "color": FG}},
        margin={"l": 40, "r": 40, "t": 50, "b": 40})
    return fig


# ──────────────────────────────────────────────
# 4. 多省雷达叠加
# ──────────────────────────────────────────────
def multi_radar(data: list[tuple[str, dict]]) -> go.Figure:
    dash_styles = ["solid", "dash", "dot", "dashdot", "longdash"]
    fig = go.Figure()

    # 动态范围：最大值恰好接触外圈
    all_vals = []
    for _, dims in data:
        all_vals.extend(dims.get(k, 0) for k in DIM_NAMES)
    r_max = max(all_vals) if all_vals else 1.0

    for i, (name, dims) in enumerate(data):
        vals = [dims.get(k, 0) for k in DIM_NAMES]
        vals.append(vals[0])
        fig.add_trace(go.Scatterpolar(
            r=vals, theta=DIM_NAMES + [DIM_NAMES[0]],
            name=name, line={"dash": dash_styles[i % 5]},
        ))
    fig.update_layout(**LAYOUT_BASE, height=480, polar={
        "radialaxis": {"gridcolor": "#E2E8F0", "range": [0, r_max]},
        "angularaxis": {"gridcolor": "#E2E8F0"},
    }, title={"text": "🎯 七维能力对比", "font": {"size": 14, "color": FG}},
        margin={"l": 40, "r": 40, "t": 50, "b": 40})
    return fig


# ──────────────────────────────────────────────
# 5. 趋势面积图
# ──────────────────────────────────────────────
def trend_area(history: list[dict], province: str) -> go.Figure:
    df = pd.DataFrame(history)
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df["年份"], y=df["综合得分"], mode="lines+markers",
        fill="tozeroy", fillcolor="rgba(30,64,175,0.06)",
        line={"color": PRIMARY, "width": 2.5}, marker={"size": 8, "color": PRIMARY},
        hovertemplate="<b>%{x}</b>: %{y:.4f}<extra></extra>",
    ))
    fig.update_layout(**LAYOUT_BASE, height=380,
                      title={"text": f"📈 {province} 历年趋势", "font": {"size": 14, "color": FG}},
                      xaxis_title=None, yaxis_title="综合得分",
                      xaxis={"dtick": 1, "gridcolor": "#E2E8F0"},
                      yaxis={"gridcolor": "#E2E8F0"},
                      margin={"l": 10, "r": 10, "t": 50, "b": 20})
    return fig


# ──────────────────────────────────────────────
# 6. 多省趋势
# ──────────────────────────────────────────────
def multi_trend(trend_data: dict[str, list[float]], years: list[int]) -> go.Figure:
    dash_styles = ["solid", "dash", "dot", "dashdot", "longdash"]
    fig = go.Figure()
    for i, (prov, scores) in enumerate(trend_data.items()):
        fig.add_trace(go.Scatter(
            x=years, y=scores, mode="lines+markers",
            name=prov, line={"dash": dash_styles[i % 5]}, marker={"size": 6},
        ))
    fig.update_layout(**LAYOUT_BASE, height=380,
                      title={"text": "📈 历年趋势对比", "font": {"size": 14, "color": FG}},
                      xaxis_title=None, yaxis_title="综合得分",
                      xaxis={"dtick": 1, "gridcolor": "#E2E8F0"},
                      yaxis={"gridcolor": "#E2E8F0"})
    return fig


# ──────────────────────────────────────────────
# 7. Moran 趋势
# ──────────────────────────────────────────────
def moran_chart(moran_rows: list[dict]) -> go.Figure:
    df = pd.DataFrame(moran_rows)
    fig = go.Figure()
    colors = [GREEN if v > 0 else MUTED for v in df["Moran_I"]]
    fig.add_trace(go.Scatter(
        x=df["年份"], y=df["Moran_I"], mode="lines+markers",
        line={"color": PRIMARY, "width": 2.5}, marker={"size": 12, "color": colors, "line": {"width": 2, "color": "white"}},
        hovertemplate="<b>%{x}</b>: Moran I = %{y:.4f}<extra></extra>",
    ))
    fig.update_layout(**LAYOUT_BASE, height=420,
                      title={"text": "🌐 Global Moran's I 历年趋势", "font": {"size": 14, "color": FG}},
                      xaxis={"dtick": 1, "gridcolor": "#E2E8F0"},
                      yaxis={"title": "Moran's I", "gridcolor": "#E2E8F0"},
                      margin={"l": 10, "r": 10, "t": 50, "b": 20})
    return fig


# ──────────────────────────────────────────────
# 8. 中国地图
# ──────────────────────────────────────────────
def china_map(ranking: list[dict]) -> go.Figure | None:
    """用 scatter_geo 在中国地图上按综合得分布点着色"""
    try:
        with open(GEOJSON_PATH) as f:
            geojson = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return None

    # 短名→全名映射
    name_map = {}
    centroids = {}
    for feat in geojson.get("features", []):
        props = feat["properties"]
        name = props.get("name", "")
        if not name:
            continue
        short = name.replace("省", "").replace("自治区", "").replace("壮族", "").replace("回族", "").replace("维吾尔", "").replace("市", "")
        if not short or short in ("香港特别行政区", "澳门特别行政区", "台湾"):
            continue
        name_map[short] = name
        center = props.get("center", props.get("centroid"))
        if center:
            centroids[name] = center  # [lon, lat]

    df = pd.DataFrame(ranking)
    df["geo_name"] = df["省份"].map(name_map)
    df["lon"] = df["geo_name"].map(lambda n: centroids.get(n, [None, None])[0])
    df["lat"] = df["geo_name"].map(lambda n: centroids.get(n, [None, None])[1])
    df = df.dropna(subset=["geo_name", "lon", "lat"])

    if df.empty:
        return None

    fig = go.Figure(go.Scattergeo(
        lon=df["lon"],
        lat=df["lat"],
        text=df["省份"] + "<br>得分: " + df["综合得分"].round(4).astype(str),
        mode="markers+text",
        marker={
            "size": df["综合得分"] * 40,
            "color": df["综合得分"],
            "colorscale": [[0, "#DBEAFE"], [0.5, "#3B82F6"], [1, PRIMARY]],
            "colorbar": {"title": "综合得分", "thickness": 15},
            "line": {"width": 1, "color": "#FFFFFF"},
            "showscale": True,
        },
        textfont={"size": 10, "color": FG},
        textposition="top center",
        hovertemplate="<b>%{text}</b><extra></extra>",
    ))
    fig.update_geos(
        visible=True,
        projection_type="natural earth",
        showcountries=False,
        showcoastlines=True,
        coastlinecolor="#CBD5E1",
        showland=True,
        landcolor="#F8FAFC",
        lataxis_range=[15, 55],
        lonaxis_range=[70, 140],
    )
    fig.update_layout(**LAYOUT_BASE, height=500,
                      title={"text": "🇨🇳 省级综合得分空间分布", "font": {"size": 14, "color": FG}},
                      margin={"l": 0, "r": 0, "t": 50, "b": 0})
    return fig


# ──────────────────────────────────────────────
# 9. 布局气泡图
# ──────────────────────────────────────────────
def layout_bubble(layout: list[dict]) -> go.Figure:
    df = pd.DataFrame(layout)
    fig = go.Figure()
    for _, s in df.iterrows():
        color = LAYOUT_COLORS.get(s["layout_type"], MUTED)
        fig.add_trace(go.Scatter(
            x=[s["avg_score"]], y=[s["count"]], mode="markers+text",
            marker={"size": s["count"] * 8, "color": color, "opacity": 0.85},
            text=[s["layout_type"]], textposition="top center",
            name=s["layout_type"], hovertemplate=f"<b>{s['layout_type']}</b><br>{s['count']}省 | 均分{s['avg_score']:.3f}<extra></extra>",
        ))
    fig.update_layout(**LAYOUT_BASE, height=360, showlegend=False,
                      xaxis_title="平均得分", yaxis_title="省份数量",
                      xaxis={"gridcolor": "#E2E8F0"}, yaxis={"gridcolor": "#E2E8F0"})
    return fig
