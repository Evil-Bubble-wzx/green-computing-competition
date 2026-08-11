"""Dashboard 图表组件 — Plotly"""

import copy
import json
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import plotly.express as px

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
# ──────────────────────────────────────────────
# 8. 中国地图
# ──────────────────────────────────────────────

def _normalize_province(name: str) -> str:
    """统一省级行政区名称：广东省→广东，新疆维吾尔自治区→新疆"""
    if name is None:
        return ""
    name = str(name).strip()
    suffixes = ["维吾尔自治区", "壮族自治区", "回族自治区", "特别行政区", "自治区", "省", "市"]
    for suffix in suffixes:
        if name.endswith(suffix):
            name = name[:-len(suffix)]
            break
    return name.strip()


def china_map(ranking: list[dict]) -> go.Figure | None:
    """中国省级 Choropleth 地图 — Choroplethmapbox, 固定视野, 不依赖 fitbounds"""

    # 1. 读取 GeoJSON
    try:
        with open(GEOJSON_PATH, "r", encoding="utf-8") as f:
            raw_geojson = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError, OSError) as e:
        print(f"[china_map] GeoJSON load failed: {e}")
        return None

    features = raw_geojson.get("features", [])
    if not features:
        print("[china_map] GeoJSON contains no features")
        return None

    # 2. 处理 ranking
    df = pd.DataFrame(ranking)
    required_columns = {"省份", "综合得分"}
    if not required_columns.issubset(df.columns):
        print("[china_map] ranking missing columns:", required_columns - set(df.columns))
        return None

    df = df.copy()
    df["province_key"] = df["省份"].astype(str).map(_normalize_province)
    df["综合得分"] = pd.to_numeric(df["综合得分"], errors="coerce")
    df = df.dropna(subset=["综合得分"])

    if df.empty:
        print("[china_map] ranking has no valid score data")
        return None

    df = df.drop_duplicates(subset=["province_key"], keep="last")
    ranking_keys = set(df["province_key"])

    # 3. 重建干净 GeoJSON：只保留 ranking 中存在的省份，id=标准化名
    clean_features = []
    geojson_keys = set()

    for feat in features:
        props = feat.get("properties") or {}
        full_name = props.get("name")
        if not full_name:
            continue
        province_key = _normalize_province(full_name)
        if not province_key:
            continue
        geojson_keys.add(province_key)
        if province_key not in ranking_keys:
            continue
        geometry = feat.get("geometry")
        if not geometry:
            continue
        geometry_type = geometry.get("type")
        if geometry_type not in ("Polygon", "MultiPolygon"):
            print(f"[china_map] skip unsupported geometry: {full_name} -> {geometry_type}")
            continue

        new_feat = copy.deepcopy(feat)
        new_feat["id"] = province_key
        clean_features.append(new_feat)

    clean_geojson = {"type": "FeatureCollection", "features": clean_features}

    # 4. 匹配检查
    rendered_keys = {f["id"] for f in clean_features}
    unmatched = sorted(ranking_keys - rendered_keys)
    print(f"[china_map] ranking={len(ranking_keys)}, geojson={len(geojson_keys)}, rendered={len(rendered_keys)}")
    if unmatched:
        print("[china_map] unmatched provinces:", unmatched)

    if not clean_features:
        print("[china_map] no matched GeoJSON features")
        return None

    plot_df = df[df["province_key"].isin(rendered_keys)].copy()
    if plot_df.empty:
        return None

    plot_df["score_rounded"] = plot_df["综合得分"].round(4)

    # 5. Choroplethmapbox — 不需要地图底图瓦片，GeoJSON 自渲染
    fig = go.Figure(go.Choroplethmapbox(
        geojson=clean_geojson,
        locations=plot_df["province_key"],
        z=plot_df["score_rounded"],
        customdata=plot_df[["省份", "score_rounded"]].to_numpy(),
        colorscale="Blues",
        marker={"opacity": 0.88, "line": {"width": 0.8}},
        colorbar={"title": "综合得分", "thickness": 15, "len": 0.70},
        hovertemplate="<b>%{customdata[0]}</b><br>综合得分：%{customdata[1]:.4f}<extra></extra>",
    ))

    # 6. 固定中国视野 — 不依赖 fitbounds
    fig.update_layout(
        **LAYOUT_BASE,
        height=500,
        title={"text": "🇨🇳 省级综合得分空间分布", "font": {"size": 14, "color": FG}},
        margin={"l": 0, "r": 0, "t": 50, "b": 0},
        mapbox={
            "style": "white-bg",
            "center": {"lat": 35.5, "lon": 104.0},
            "zoom": 2.7,
        },
    )
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
