"""
Dashboard-DB 一致性检查 (H5)

验证 Dashboard 各页面调用的 QueryEngine 方法返回结果与底层 DB 表一致。
纯后端验证，不启动 Streamlit。

覆盖:
  - overview: 排名列表、布局汇总、边界省份
  - province: 省份摘要、维度得分、得分历史
  - comparison: 多省查询排名一致性
  - spatial: LISA 显著省份
  - layout_page: 布局-省份对应关系
  - 跨页一致性: 排名第一省份在各页中一致
"""

from __future__ import annotations

from dataclasses import dataclass, field

from sqlalchemy import text

from src.data.database import DatabaseManager
from src.data.queries import QueryEngine, TBL_GOLDEN, TBL_SCORE, TBL_DIM

VALID_LAYOUTS = ["高适宜综合承载区", "需求网络驱动区", "能源低碳优势承接区", "综合潜力提升区", "约束控制区"]
VALID_LISA_TYPES = {"高-高集聚", "高-低离群", "低-高离群", "低-低集聚", "不显著"}
PROVINCE_COUNT = 31
YEAR_RANGE = range(2016, 2025)


@dataclass
class ConsistencyCheck:
    """单条一致性检查"""
    page: str               # Dashboard 页面名
    check_name: str         # 检查项名称
    query_method: str       # 被测 QueryEngine 方法
    passed: bool
    detail: str = ""


@dataclass
class DashboardConsistencySuite:
    """完整 Dashboard 一致性套件"""
    total: int = 0
    passed: int = 0
    checks: list[ConsistencyCheck] = field(default_factory=list)

    @property
    def pass_rate(self) -> float:
        return self.passed / self.total if self.total > 0 else 0


class DashboardConsistencyChecker:
    """Dashboard-DB 一致性检查器

    用法:
        checker = DashboardConsistencyChecker(query_engine)
        suite = checker.run_all()
    """

    def __init__(self, query_engine: QueryEngine):
        self.qe = query_engine

    # ------------------------------------------------------------------
    # 主入口
    # ------------------------------------------------------------------

    def run_all(self) -> DashboardConsistencySuite:
        suite = DashboardConsistencySuite()

        # === overview 页 ===
        self._check_ranking(suite)
        self._check_layout_summary(suite)
        self._check_boundary(suite)
        self._check_layout_province_mapping(suite)

        # === province 页 ===
        self._check_province_summary(suite)
        self._check_dimension_scores(suite)
        self._check_score_history(suite)

        # === comparison 页 ===
        self._check_multi_province_consistency(suite)

        # === spatial 页 ===
        self._check_lisa(suite)

        # === layout_page 页 ===
        self._check_layout_detail(suite)

        # === 跨页一致性 ===
        self._check_cross_page(suite)

        suite.total = len(suite.checks)
        suite.passed = sum(1 for c in suite.checks if c.passed)
        return suite

    # ------------------------------------------------------------------
    # Overview 页检查
    # ------------------------------------------------------------------

    def _check_ranking(self, suite: DashboardConsistencySuite):
        """排名列表应包含31省，按排名升序"""
        ranking = self.qe.get_score_ranking(2024)
        rank_values = [r["排名"] for r in ranking]

        # 数量
        suite.checks.append(ConsistencyCheck(
            page="overview", check_name="排名列表31行",
            query_method="get_score_ranking(2024)",
            passed=len(ranking) == PROVINCE_COUNT,
            detail=f"返回{len(ranking)}行" + ("" if len(ranking) == PROVINCE_COUNT else f" (期望{PROVINCE_COUNT})"),
        ))

        # 排序
        is_sorted = rank_values == sorted(rank_values)
        suite.checks.append(ConsistencyCheck(
            page="overview", check_name="排名升序",
            query_method="get_score_ranking(2024)",
            passed=is_sorted,
            detail="排名正确排序" if is_sorted else f"排序错误: {rank_values[:5]}...",
        ))

        # Top1 与 DB 直接查询一致
        if ranking:
            top1 = ranking[0]
            db_row = self._raw_one(
                f'SELECT "省份", "综合得分" FROM "{TBL_SCORE}" WHERE "年份" = 2024 ORDER BY "排名" LIMIT 1'
            )
            match = db_row and top1["省份"] == db_row["省份"]
            suite.checks.append(ConsistencyCheck(
                page="overview", check_name="Top1 省份一致",
                query_method="get_score_ranking(2024)[0]",
                passed=bool(match),
                detail=f"Top1={top1['省份']} DB={db_row['省份'] if db_row else 'N/A'}",
            ))

    def _check_layout_summary(self, suite: DashboardConsistencySuite):
        """布局汇总：5类型，总数=31，得分合理"""
        layout = self.qe.get_layout_summary()

        # 类型数量
        suite.checks.append(ConsistencyCheck(
            page="overview", check_name="5布局类型",
            query_method="get_layout_summary()",
            passed=len(layout) == 5,
            detail=f"返回{len(layout)}种布局",
        ))

        # 各省计数总和
        total = sum(s["count"] for s in layout)
        suite.checks.append(ConsistencyCheck(
            page="overview", check_name="布局总数=31",
            query_method="get_layout_summary()",
            passed=total == PROVINCE_COUNT,
            detail=f"各省计数和={total}" + ("" if total == PROVINCE_COUNT else f" (期望{PROVINCE_COUNT})"),
        ))

        # 平均得分在 [0,1] 范围
        scores_ok = all(0 <= s["avg_score"] <= 1 for s in layout)
        suite.checks.append(ConsistencyCheck(
            page="overview", check_name="平均得分范围[0,1]",
            query_method="get_layout_summary()",
            passed=scores_ok,
            detail="全部在[0,1]" if scores_ok else "存在超出范围的值",
        ))

        # 与 DB 原始查询比较
        for lt in layout:
            db_count = self._raw_scalar(
                f'SELECT COUNT(*) FROM "{TBL_GOLDEN}" WHERE "最终布局类型(V2A口径兼容)" = :lt',
                {"lt": lt["layout_type"]},
            )
            if db_count != lt["count"]:
                suite.checks.append(ConsistencyCheck(
                    page="overview", check_name=f"{lt['layout_type']}数量一致",
                    query_method="get_layout_summary()",
                    passed=False,
                    detail=f"方法={lt['count']} DB={db_count}",
                ))
                return
        suite.checks.append(ConsistencyCheck(
            page="overview", check_name="所有布局数量与DB一致",
            query_method="get_layout_summary()",
            passed=True, detail="5/5一致",
        ))

    def _check_boundary(self, suite: DashboardConsistencySuite):
        """边界省份检查"""
        boundary = self.qe.get_boundary_provinces()

        # 所有边界省份 keep_prob < 0.80
        all_under_80 = all(b["keep_prob"] < 0.80 for b in boundary)
        suite.checks.append(ConsistencyCheck(
            page="overview", check_name="边界省keep_prob<0.80",
            query_method="get_boundary_provinces()",
            passed=all_under_80,
            detail="全部<0.80" if all_under_80 else "存在>=0.80的省份",
        ))

        # 与 DB 原始查询一致
        db_boundary = self._raw_all(
            f'SELECT "省份" FROM "{TBL_GOLDEN}" WHERE "内部稳定性标签" = \'边界型\''
        )
        match = len(boundary) == len(db_boundary)
        suite.checks.append(ConsistencyCheck(
            page="overview", check_name="边界省数量与DB一致",
            query_method="get_boundary_provinces()",
            passed=match,
            detail=f"方法={len(boundary)} DB={len(db_boundary)}",
        ))

    def _check_layout_province_mapping(self, suite: DashboardConsistencySuite):
        """get_provinces_by_layout 返回的省份列表正确"""
        for layout_name in VALID_LAYOUTS:
            provs = self.qe.get_provinces_by_layout(layout_name)
            db_provs = self._raw_all(
                f'SELECT "省份" FROM "{TBL_GOLDEN}" '
                f'WHERE "最终布局类型(V2A口径兼容)" = :lt ORDER BY "全国综合得分排名"',
                {"lt": layout_name},
            )
            expected = [r["省份"] for r in db_provs]
            if provs != expected:
                suite.checks.append(ConsistencyCheck(
                    page="overview", check_name=f"{layout_name}省份列表一致",
                    query_method="get_provinces_by_layout()",
                    passed=False,
                    detail=f"方法={provs[:3]}... DB={expected[:3]}...",
                ))
                return
        suite.checks.append(ConsistencyCheck(
            page="overview", check_name="5布局省份列表100%一致",
            query_method="get_provinces_by_layout()",
            passed=True, detail="5/5正确",
        ))

    # ------------------------------------------------------------------
    # Province 页检查
    # ------------------------------------------------------------------

    def _check_province_summary(self, suite: DashboardConsistencySuite):
        """省份摘要：关键字段非空且类型正确"""
        summary = self.qe.get_province_summary("江苏")

        fields_ok = (
            summary.province == "江苏"
            and isinstance(summary.score_rank, int) and 1 <= summary.score_rank <= PROVINCE_COUNT
            and isinstance(summary.composite_score, float) and 0 < summary.composite_score <= 1
            and len(summary.layout_type) > 0
        )
        suite.checks.append(ConsistencyCheck(
            page="province", check_name="江苏摘要字段正确",
            query_method="get_province_summary('江苏')",
            passed=fields_ok,
            detail=f"rank={summary.score_rank} score={summary.composite_score:.4f} layout={summary.layout_type}",
        ))

    def _check_dimension_scores(self, suite: DashboardConsistencySuite):
        """七维得分：返回7个维度，值在[0,1]"""
        dims = self.qe.get_dimension_scores("江苏", 2024)

        has_7 = len(dims) == 7
        all_valid = all(0 <= v <= 1 for v in dims.values())
        suite.checks.append(ConsistencyCheck(
            page="province", check_name="七维得分完整",
            query_method="get_dimension_scores('江苏', 2024)",
            passed=has_7 and all_valid,
            detail=f"{len(dims)}维" + ("" if has_7 else " (期望7)"),
        ))

    def _check_score_history(self, suite: DashboardConsistencySuite):
        """得分历史：9年数据(2016-2024)，按年份排序"""
        history = self.qe.get_score_history("江苏")

        years = [h["年份"] for h in history]
        has_9 = len(history) == 9
        sorted_by_year = years == sorted(years)
        suite.checks.append(ConsistencyCheck(
            page="province", check_name="得分历史9年排序",
            query_method="get_score_history('江苏')",
            passed=has_9 and sorted_by_year,
            detail=f"{len(history)}年, 年份{'有序' if sorted_by_year else '无序'}",
        ))

    # ------------------------------------------------------------------
    # Comparison 页检查
    # ------------------------------------------------------------------

    def _check_multi_province_consistency(self, suite: DashboardConsistencySuite):
        """多省对比：get_top_n(3) 与 get_score_ranking 的前3一致"""
        top3 = self.qe.get_top_n(3, 2024)
        ranking = self.qe.get_score_ranking(2024)

        match = (
            len(top3) == 3
            and top3[0]["省份"] == ranking[0]["省份"]
            and top3[1]["省份"] == ranking[1]["省份"]
            and top3[2]["省份"] == ranking[2]["省份"]
        )
        suite.checks.append(ConsistencyCheck(
            page="comparison", check_name="Top3与排名列表一致",
            query_method="get_top_n(3, 2024)",
            passed=match,
            detail="一致" if match else f"Top3={[t['省份'] for t in top3]} Ranking前3={[r['省份'] for r in ranking[:3]]}",
        ))

    # ------------------------------------------------------------------
    # Spatial 页检查
    # ------------------------------------------------------------------

    def _check_lisa(self, suite: DashboardConsistencySuite):
        """LISA显著省份：无不显著标记"""
        lisa = self.qe.get_significant_lisa()

        no_ns = all(r["lisa_type"] != "不显著" for r in lisa)
        suite.checks.append(ConsistencyCheck(
            page="spatial", check_name="LISA显著省无不显著",
            query_method="get_significant_lisa()",
            passed=no_ns,
            detail=f"{len(lisa)}省显著" + ("" if no_ns else " 存在不显著标记"),
        ))

    # ------------------------------------------------------------------
    # Layout 页检查
    # ------------------------------------------------------------------

    def _check_layout_detail(self, suite: DashboardConsistencySuite):
        """布局详情：get_layout_summary count = len(get_provinces_by_layout)"""
        layout = self.qe.get_layout_summary()
        all_match = True
        for lt in layout:
            provs = self.qe.get_provinces_by_layout(lt["layout_type"])
            if lt["count"] != len(provs):
                all_match = False
                suite.checks.append(ConsistencyCheck(
                    page="layout_page", check_name=f"{lt['layout_type']}数量自洽",
                    query_method="get_layout_summary + get_provinces_by_layout",
                    passed=False,
                    detail=f"summary={lt['count']} provinces={len(provs)}",
                ))
                return
        suite.checks.append(ConsistencyCheck(
            page="layout_page", check_name="5布局count=provinces列表长度",
            query_method="get_layout_summary + get_provinces_by_layout",
            passed=True, detail="5/5自洽",
        ))

    # ------------------------------------------------------------------
    # 跨页一致性
    # ------------------------------------------------------------------

    def _check_cross_page(self, suite: DashboardConsistencySuite):
        """跨页验证：overview #1 = province 页该省 rank"""
        ranking = self.qe.get_score_ranking(2024)
        top1_province = ranking[0]["省份"]
        top1_summary = self.qe.get_province_summary(top1_province)

        suite.checks.append(ConsistencyCheck(
            page="cross-page", check_name=f"overview#1={top1_province}与province页rank一致",
            query_method="get_score_ranking + get_province_summary",
            passed=top1_summary.score_rank == 1,
            detail=f"{top1_province} rank={top1_summary.score_rank}",
        ))

        # 布局汇总与各省摘要一致
        layout = self.qe.get_layout_summary()
        for lt in layout:
            provs = self.qe.get_provinces_by_layout(lt["layout_type"])
            if provs:
                sample = self.qe.get_province_summary(provs[0])
                if sample.layout_type != lt["layout_type"]:
                    suite.checks.append(ConsistencyCheck(
                        page="cross-page", check_name=f"{provs[0]}布局类型一致",
                        query_method="get_province_summary",
                        passed=False,
                        detail=f"summary={sample.layout_type} layout={lt['layout_type']}",
                    ))
                    return
        suite.checks.append(ConsistencyCheck(
            page="cross-page", check_name="各省布局类型与汇总一致",
            query_method="get_layout_summary ↔ get_province_summary",
            passed=True, detail="已抽查验证",
        ))

    # ------------------------------------------------------------------
    # 原始 SQL 查询辅助
    # ------------------------------------------------------------------

    def _raw_one(self, sql: str, params: dict | None = None) -> dict | None:
        """执行原始 SQL，返回单行"""
        with self.qe.db.session() as sess:
            row = sess.execute(text(sql), params or {}).fetchone()
            return dict(row._mapping) if row else None

    def _raw_all(self, sql: str, params: dict | None = None) -> list[dict]:
        """执行原始 SQL，返回所有行"""
        with self.qe.db.session() as sess:
            rows = sess.execute(text(sql), params or {}).fetchall()
            return [dict(r._mapping) for r in rows]

    def _raw_scalar(self, sql: str, params: dict | None = None):
        """执行原始 SQL，返回标量"""
        with self.qe.db.session() as sess:
            return sess.execute(text(sql), params or {}).scalar()
