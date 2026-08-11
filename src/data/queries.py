"""
结构化数据查询引擎 (纯 SQL)

直接对导入的数据库表执行查询，不经过 ORM。
所有表名和列名与 Navicat 中看到的一致。
"""

from dataclasses import dataclass
from typing import Optional

from sqlalchemy import text

from src.data.database import DatabaseManager
from src.core.exceptions import ProvinceNotFoundError, YearNotAvailableError

# =========================================================================
# 表名常量（与 Navicat 中看到的完全一致）
# =========================================================================

TBL_GOLDEN = "01_系统标准答案_Golden_Set_31省最终GoldenSet"
TBL_SCORE = "05_综合评价核心结果_NAT_FINAL_综合得分"
TBL_DIM = "05_综合评价核心结果_NAT_FINAL_七维得分"
TBL_INDICATOR = "05_综合评价核心结果_NAT_FINAL_指标字典"
TBL_LPA = "05_综合评价核心结果_NAT_FINAL_LPA省份归属"
TBL_RAW = "05_综合评价核心结果_NAT_FINAL_清洗数据"


@dataclass
class ProvinceSummary:
    province: str
    score_rank: int
    composite_score: float
    layout_type: str
    lpa_type_name: str = ""
    stability_label: str = ""
    lisa_type_2024: str = "不显著"
    is_hub: bool = False
    green_dc_count_2023: int = 0
    keep_baseline_prob: float = 0.0


class QueryEngine:
    """纯 SQL 查询引擎"""

    VALID_YEARS = range(2016, 2025)

    def __init__(self, db: DatabaseManager):
        self.db = db

    def _one(self, sql: str, params: dict | None = None) -> dict | None:
        """执行查询并返回单行 dict"""
        with self.db.session() as sess:
            result = sess.execute(text(sql), params or {})
            row = result.fetchone()
            return dict(row._mapping) if row else None

    def _all(self, sql: str, params: dict | None = None) -> list[dict]:
        """执行查询并返回 dict 列表"""
        with self.db.session() as sess:
            result = sess.execute(text(sql), params or {})
            return [dict(row._mapping) for row in result.fetchall()]

    # -----------------------------------------------------------------
    # 省份查询
    # -----------------------------------------------------------------

    def list_all_provinces(self) -> list[str]:
        rows = self._all(f'SELECT "省份" FROM "{TBL_GOLDEN}" ORDER BY "全国综合得分排名"')
        return [r["省份"] for r in rows]

    def get_province_summary(self, province: str) -> ProvinceSummary:
        row = self._one(
            f'SELECT * FROM "{TBL_GOLDEN}" WHERE "省份" = :p', {"p": province}
        )
        if not row:
            raise ProvinceNotFoundError(province)

        # 尝试获取 LPA 类型
        lpa_row = self._one(
            f'SELECT "类型命名" FROM "{TBL_LPA}" WHERE "省份" = :p', {"p": province}
        )

        return ProvinceSummary(
            province=row["省份"],
            score_rank=row["全国综合得分排名"],
            composite_score=round(row["综合得分"], 6),
            layout_type=row["最终布局类型(V2A口径兼容)"],
            lpa_type_name=lpa_row["类型命名"] if lpa_row else "",
            stability_label=row["内部稳定性标签"],
            lisa_type_2024=row["2024修正LISA类型"],
            is_hub=row["国家枢纽省份"] == "是",
            green_dc_count_2023=row["2023国家绿色数据中心数"],
            keep_baseline_prob=float(row.get("保持原布局概率", 0)),
        )

    # -----------------------------------------------------------------
    # 排名与得分
    # -----------------------------------------------------------------

    def get_top_n(self, n: int = 5, year: int = 2024) -> list[dict]:
        if year not in self.VALID_YEARS:
            raise YearNotAvailableError(year)
        return self._all(
            f'SELECT "省份", "综合得分", "排名" FROM "{TBL_SCORE}" '
            f'WHERE "年份" = :y ORDER BY "排名" LIMIT :n',
            {"y": year, "n": n},
        )

    def get_score_ranking(self, year: int = 2024) -> list[dict]:
        if year not in self.VALID_YEARS:
            raise YearNotAvailableError(year)
        return self._all(
            f'SELECT "省份", "综合得分", "排名" FROM "{TBL_SCORE}" '
            f'WHERE "年份" = :y ORDER BY "排名"',
            {"y": year},
        )

    def get_score_history(self, province: str) -> list[dict]:
        return self._all(
            f'SELECT "年份", "综合得分", "排名" FROM "{TBL_SCORE}" '
            f'WHERE "省份" = :p ORDER BY "年份"',
            {"p": province},
        )

    # -----------------------------------------------------------------
    # 维度
    # -----------------------------------------------------------------

    def get_dimension_scores(self, province: str, year: int = 2024) -> dict:
        if year not in self.VALID_YEARS:
            raise YearNotAvailableError(year)
        row = self._one(
            f'SELECT * FROM "{TBL_DIM}" WHERE "省份" = :p AND "年份" = :y',
            {"p": province, "y": year},
        )
        if not row:
            return {}
        return {
            "算力需求基础": row.get("算力需求基础", 0),
            "数字基础设施": row.get("数字基础设施", 0),
            "能源供给能力": row.get("能源供给能力", 0),
            "绿色低碳约束": row.get("绿色低碳约束", 0),
            "气候与自然条件": row.get("气候与自然条件", 0),
            "创新与人才支撑": row.get("创新与人才支撑", 0),
            "区域协同能力": row.get("区域协同能力", 0),
        }

    # -----------------------------------------------------------------
    # 分类查询
    # -----------------------------------------------------------------

    def get_provinces_by_layout(self, layout_type: str) -> list[str]:
        rows = self._all(
            f'SELECT "省份" FROM "{TBL_GOLDEN}" '
            f'WHERE "最终布局类型(V2A口径兼容)" = :lt ORDER BY "全国综合得分排名"',
            {"lt": layout_type},
        )
        return [r["省份"] for r in rows]

    def get_layout_summary(self) -> list[dict]:
        layouts = ["高适宜综合承载区", "需求网络驱动区", "能源低碳优势承接区", "综合潜力提升区", "约束控制区"]
        result = []
        for lt in layouts:
            rows = self._all(
                f'SELECT * FROM "{TBL_GOLDEN}" WHERE "最终布局类型(V2A口径兼容)" = :lt',
                {"lt": lt},
            )
            if rows:
                scores = [r["综合得分"] for r in rows]
                dc = sum(r["2023国家绿色数据中心数"] for r in rows)
                hubs = sum(1 for r in rows if r["国家枢纽省份"] == "是")
                result.append({
                    "layout_type": lt,
                    "count": len(rows),
                    "avg_score": round(sum(scores) / len(scores), 4),
                    "green_dc_total": dc,
                    "hub_count": hubs,
                })
        return result

    def get_boundary_provinces(self) -> list[dict]:
        rows = self._all(
            f'SELECT "省份", "最终布局类型(V2A口径兼容)", "保持原布局概率" '
            f'FROM "{TBL_GOLDEN}" WHERE "内部稳定性标签" = :s '
            f'ORDER BY "保持原布局概率"',
            {"s": "边界型"},
        )
        return [
            {"province": r["省份"], "layout_type": r["最终布局类型(V2A口径兼容)"], "keep_prob": r["保持原布局概率"]}
            for r in rows
        ]

    def get_significant_lisa(self) -> list[dict]:
        rows = self._all(
            f'SELECT "省份", "2024修正LISA类型", "综合得分" FROM "{TBL_GOLDEN}" '
            f'WHERE "2024修正LISA类型" != :ns',
            {"ns": "不显著"},
        )
        return [
            {"province": r["省份"], "lisa_type": r["2024修正LISA类型"], "score": r["综合得分"]}
            for r in rows
        ]
