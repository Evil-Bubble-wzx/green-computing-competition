"""
Data Query MCP 工具集

每个工具对应一个绿色算力数据查询能力。
"""

import asyncio
import json

from src.data.database import DatabaseManager
from src.data.queries import QueryEngine


def _make_async(fn):
    """将同步函数包装为 awaitable"""
    async def wrapper(**kwargs):
        return await asyncio.to_thread(fn, **kwargs)
    return wrapper


def register_all(handler, db_manager: DatabaseManager | None, query_engine: QueryEngine | None):
    """注册所有工具到 ProtocolHandler"""

    # 如果没有传入，自行创建
    if query_engine is None and db_manager is not None:
        query_engine = QueryEngine(db_manager)
    if query_engine is None:
        return  # 没有数据库连接，跳过注册

    qe = query_engine

    # ------------------------------------------------------------------
    # 1. list_provinces
    # ------------------------------------------------------------------
    async def list_provinces():
        """列出所有 31 个省份标准名称（按排名）"""
        provinces = qe.list_all_provinces()
        return json.dumps({"count": len(provinces), "provinces": provinces}, ensure_ascii=False)

    handler.register_tool(
        "list_provinces",
        "列出中国 31 个省级行政区（按综合得分排名）",
        {"type": "object", "properties": {}, "required": []},
        list_provinces,
    )

    # ------------------------------------------------------------------
    # 2. query_province_score
    # ------------------------------------------------------------------
    async def query_province_score(province: str, year: int = 2024):
        """查询指定省份的综合得分和排名"""
        summary = qe.get_province_summary(province)
        dims = qe.get_dimension_scores(province, year)
        return json.dumps({
            "province": summary.province,
            "year": year,
            "score": summary.composite_score,
            "rank": summary.score_rank,
            "layout_type": summary.layout_type,
            "lpa_type": summary.lpa_type_name,
            "stability": summary.stability_label,
            "lisa_2024": summary.lisa_type_2024,
            "is_hub": summary.is_hub,
            "green_dc_count": summary.green_dc_count_2023,
            "dimensions": dims,
        }, ensure_ascii=False)

    handler.register_tool(
        "query_province_score",
        "查询指定省份的绿色算力综合得分、排名、布局类型和七维得分",
        {
            "type": "object",
            "properties": {
                "province": {"type": "string", "description": "省份标准名称，如'江苏'、'广东'"},
                "year": {"type": "integer", "description": "年份 (2016-2024)，默认2024", "default": 2024},
            },
            "required": ["province"],
        },
        query_province_score,
    )

    # ------------------------------------------------------------------
    # 3. compare_provinces
    # ------------------------------------------------------------------
    async def compare_provinces(provinces: list[str], year: int = 2024):
        """多省份对比"""
        result = []
        for p in provinces:
            try:
                summary = qe.get_province_summary(p)
                result.append({
                    "province": p,
                    "score": summary.composite_score,
                    "rank": summary.score_rank,
                    "layout_type": summary.layout_type,
                    "lpa_type": summary.lpa_type_name,
                    "stability": summary.stability_label,
                })
            except Exception as e:
                result.append({"province": p, "error": str(e)})
        return json.dumps({"year": year, "provinces": result}, ensure_ascii=False)

    handler.register_tool(
        "compare_provinces",
        "对比多个省份的综合得分、排名和布局类型",
        {
            "type": "object",
            "properties": {
                "provinces": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "需要对比的省份列表，如 ['江苏', '广东', '北京']",
                },
                "year": {"type": "integer", "description": "年份 (2016-2024)，默认2024"},
            },
            "required": ["provinces"],
        },
        compare_provinces,
    )

    # ------------------------------------------------------------------
    # 4. get_trend
    # ------------------------------------------------------------------
    async def get_trend(province: str):
        """获取省份历年得分趋势"""
        history = qe.get_score_history(province)
        return json.dumps({"province": province, "history": history}, ensure_ascii=False)

    handler.register_tool(
        "get_trend",
        "查询指定省份 2016-2024 年的综合得分变化趋势",
        {
            "type": "object",
            "properties": {
                "province": {"type": "string", "description": "省份标准名称"},
            },
            "required": ["province"],
        },
        get_trend,
    )

    # ------------------------------------------------------------------
    # 5. query_layout
    # ------------------------------------------------------------------
    async def query_layout(layout_type: str = ""):
        """查询布局分类"""
        if layout_type:
            provinces = qe.get_provinces_by_layout(layout_type)
            return json.dumps({"layout_type": layout_type, "count": len(provinces), "provinces": provinces}, ensure_ascii=False)
        else:
            summary = qe.get_layout_summary()
            return json.dumps(summary, ensure_ascii=False)

    handler.register_tool(
        "query_layout",
        "查询五类布局（高适宜综合承载区/需求网络驱动区/能源低碳优势承接区/综合潜力提升区/约束控制区）的省份分布",
        {
            "type": "object",
            "properties": {
                "layout_type": {"type": "string", "description": "布局类型名称，留空则返回全部五类的汇总统计"},
            },
            "required": [],
        },
        query_layout,
    )

    # ------------------------------------------------------------------
    # 6. get_dimensions
    # ------------------------------------------------------------------
    async def get_dimensions(province: str, year: int = 2024):
        """查询七维得分"""
        dims = qe.get_dimension_scores(province, year)
        return json.dumps({"province": province, "year": year, "dimensions": dims}, ensure_ascii=False)

    handler.register_tool(
        "get_dimensions",
        "查询指定省份的七维得分（算力需求基础/数字基础设施/能源供给能力/绿色低碳约束/气候与自然条件/创新与人才支撑/区域协同能力）",
        {
            "type": "object",
            "properties": {
                "province": {"type": "string", "description": "省份标准名称"},
                "year": {"type": "integer", "description": "年份 (2016-2024)，默认2024"},
            },
            "required": ["province"],
        },
        get_dimensions,
    )

    # ------------------------------------------------------------------
    # 7. get_boundary_provinces
    # ------------------------------------------------------------------
    async def get_boundary_provinces():
        """获取布局边界省份"""
        boundary = qe.get_boundary_provinces()
        return json.dumps({"边界型省份": boundary}, ensure_ascii=False)

    handler.register_tool(
        "get_boundary_provinces",
        "获取布局类型不稳定的边界省份（保持率 < 80%）",
        {"type": "object", "properties": {}, "required": []},
        get_boundary_provinces,
    )

    # ------------------------------------------------------------------
    # 8. get_ranking
    # ------------------------------------------------------------------
    async def get_ranking(year: int = 2024, top_n: int = 10):
        """获取前 N 名排名"""
        top = qe.get_top_n(top_n, year)
        all_ranks = qe.get_score_ranking(year)
        return json.dumps({
            "year": year,
            f"top_{top_n}": top,
            "full_ranking": all_ranks,
        }, ensure_ascii=False)

    handler.register_tool(
        "get_ranking",
        "获取指定年份的全国综合得分排名",
        {
            "type": "object",
            "properties": {
                "year": {"type": "integer", "description": "年份 (2016-2024)，默认2024"},
                "top_n": {"type": "integer", "description": "返回前 N 名，默认10"},
            },
            "required": [],
        },
        get_ranking,
    )
