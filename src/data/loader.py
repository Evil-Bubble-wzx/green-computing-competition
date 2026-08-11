"""
Excel → 数据库 导入器

将 NAT_FINAL 冻结的 Excel 数据导入 SQLite 数据库。
核心原则: 导入后必须与 Golden Set 做逐字段差分验证。
"""

import re
from pathlib import Path
from typing import Optional

import pandas as pd

from src.data.database import DatabaseManager
from src.data.models import (
    ProvinceGolden,
    ProvinceScoreYearly,
    ProvinceDimensionScore,
    IndicatorDict,
    LPAProvinceType,
)


class DataLoader:
    """
    NAT_FINAL Excel 数据导入器。

    用法:
        loader = DataLoader(db_manager, docx_dir="./docx")
        loader.load_all()         # 导入所有数据
        loader.verify_golden()    # 验证与 Golden Set 一致性
    """

    # 标准31省名称列表
    STANDARD_PROVINCES = [
        "北京", "天津", "河北", "山西", "内蒙古",
        "辽宁", "吉林", "黑龙江",
        "上海", "江苏", "浙江", "安徽", "福建", "江西", "山东",
        "河南", "湖北", "湖南", "广东", "广西", "海南",
        "重庆", "四川", "贵州", "云南", "西藏",
        "陕西", "甘肃", "青海", "宁夏", "新疆",
    ]

    def __init__(self, db: DatabaseManager, docx_dir: str | Path = "./docx"):
        self.db = db
        self.docx_dir = Path(docx_dir)
        self._golden_df: Optional[pd.DataFrame] = None

    # =========================================================================
    # 主流程
    # =========================================================================

    def load_all(self) -> dict[str, int]:
        """
        导入所有数据文件到数据库。

        Returns:
            dict: 各表导入行数 {"golden": 31, "scores": 279, ...}
        """
        self.db.initialize()
        counts = {}

        counts["golden"] = self.load_golden_set()
        counts["scores"] = self.load_yearly_scores()
        counts["dimensions"] = self.load_dimension_scores()
        counts["indicators"] = self.load_indicator_dict()
        counts["lpa"] = self.load_lpa_types()

        return counts

    # =========================================================================
    # 各表导入
    # =========================================================================

    def load_golden_set(self) -> int:
        """导入 Golden Set → province_golden 表"""
        path = self.docx_dir / "01_系统标准答案_Golden_Set.xlsx"
        df = pd.read_excel(path, sheet_name="31省最终GoldenSet")
        self._golden_df = df  # 缓存用于后续验证

        column_map = {
            "省份": "province",
            "全国综合得分排名": "score_rank",
            "综合得分": "composite_score",
            "阶段增量": "growth",
            "需求网络优势": "demand_idx",
            "能源低碳优势": "energy_idx",
            "约束压力": "constraint_idx",
            "综合适宜度": "suitability",
            "适宜度排名": "suit_rank",
            "最终布局类型(V2A口径兼容)": "layout_type",
            "2023国家绿色数据中心数": "green_dc_count_2023",
            "国家枢纽省份": "is_hub",
            "保持原布局概率": "keep_baseline_prob",
            "内部稳定性标签": "stability_label",
            "2024修正LISA类型": "lisa_type_2024",
            "进入Top5概率": "top5_prob",
            "进入Bottom4概率": "bottom4_prob",
        }
        df = df.rename(columns=column_map)
        df["is_hub"] = df["is_hub"].map({"是": True, "否": False})

        with self.db.session() as sess:
            for _, row in df.iterrows():
                record = ProvinceGolden(**row.to_dict())
                sess.add(record)
            sess.commit()

        return len(df)

    def load_yearly_scores(self) -> int:
        """导入逐年综合得分"""
        path = self.docx_dir / "05_综合评价核心结果_NAT_FINAL.xlsx"
        df = pd.read_excel(path, sheet_name="综合得分")

        count = 0
        with self.db.session() as sess:
            for _, row in df.iterrows():
                # 综合得分 sheet 的列名格式: "省份", "年份", "综合得分", "排名"
                record = ProvinceScoreYearly(
                    province=row.get("省份", row.iloc[0]),
                    year=int(row.get("年份", row.iloc[1])),
                    composite_score=float(row.get("综合得分", row.iloc[2])),
                    rank=int(row.get("排名", row.iloc[3])),
                )
                sess.add(record)
                count += 1
            sess.commit()

        return count

    def load_dimension_scores(self) -> int:
        """导入七维得分"""
        path = self.docx_dir / "05_综合评价核心结果_NAT_FINAL.xlsx"
        df = pd.read_excel(path, sheet_name="七维得分")

        dim_columns = {
            "算力需求基础": "dim_demand",
            "数字基础设施": "dim_digital_infra",
            "能源供给能力": "dim_energy",
            "绿色低碳约束": "dim_green_lowcarbon",
            "气候与自然条件": "dim_climate_nature",
            "创新与人才支撑": "dim_innovation_talent",
            "区域协同能力": "dim_regional_synergy",
        }

        count = 0
        with self.db.session() as sess:
            for _, row in df.iterrows():
                data = {
                    "province": row["省份"],
                    "year": int(row["年份"]),
                }
                for cn_name, en_name in dim_columns.items():
                    if cn_name in row:
                        data[en_name] = float(row[cn_name])
                sess.add(ProvinceDimensionScore(**data))
                count += 1
            sess.commit()

        return count

    def load_indicator_dict(self) -> int:
        """导入34项指标字典"""
        path = self.docx_dir / "05_综合评价核心结果_NAT_FINAL.xlsx"
        df = pd.read_excel(path, sheet_name="指标字典")

        column_map = {
            "指标代码": "code",
            "指标名称": "name",
            "一级维度": "dimension",
            "指标方向": "direction",
        }
        df = df.rename(columns=column_map)

        count = 0
        with self.db.session() as sess:
            for _, row in df.iterrows():
                sess.add(IndicatorDict(**row.to_dict()))
                count += 1
            sess.commit()

        return count

    def load_lpa_types(self) -> int:
        """导入 LPA 省份类型归属"""
        path = self.docx_dir / "05_综合评价核心结果_NAT_FINAL.xlsx"
        df = pd.read_excel(path, sheet_name="LPA省份归属")

        count = 0
        with self.db.session() as sess:
            for _, row in df.iterrows():
                record = LPAProvinceType(
                    province=str(row["省份"]),
                    lpa_type=int(row.get("LPA类型", row.get("类型", 0))),
                    lpa_type_name=str(row.get("类型命名", "")),
                    max_posterior=float(row.get("最大后验概率", 0)),
                    stability_label=str(row.get("内部稳定性标签", "")),
                    is_boundary=row.get("是否边界型", "否") == "是",
                )
                sess.add(record)
                count += 1
            sess.commit()

        return count

    # =========================================================================
    # 验证
    # =========================================================================

    def verify_golden(self) -> list[str]:
        """
        验证数据库中 Golden Set 表的数据完整性。

        Returns:
            list[str]: 问题列表。空列表 = 验证通过。
        """
        issues = []

        with self.db.session() as sess:
            records = sess.query(ProvinceGolden).all()
            provinces_in_db = {r.province for r in records}

            # 检查省份数量
            if len(records) != 31:
                issues.append(f"省份数量: {len(records)} (期望 31)")

            # 检查缺失省份
            missing = set(self.STANDARD_PROVINCES) - provinces_in_db
            if missing:
                issues.append(f"缺失省份: {missing}")

            # 检查多余省份
            extra = provinces_in_db - set(self.STANDARD_PROVINCES)
            if extra:
                issues.append(f"多余省份: {extra}")

            # 检查 NULL 值
            for r in records:
                for field in ["composite_score", "score_rank", "layout_type"]:
                    if getattr(r, field) is None:
                        issues.append(f"{r.province}.{field} 为 NULL")

        return issues
