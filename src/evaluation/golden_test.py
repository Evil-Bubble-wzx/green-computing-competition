"""
Golden Set 一致性回归测试

逐字段验证数据库中的数据与 docx/01_系统标准答案_Golden_Set.xlsx 一致。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd
from sqlalchemy import text

from src.data.database import DatabaseManager
from src.data.queries import QueryEngine, TBL_GOLDEN


@dataclass
class GoldenTestResult:
    """Golden Set 测试结果"""
    total_checks: int = 0
    passed: int = 0
    failed: int = 0
    errors: list[str] = field(default_factory=list)
    details: list[dict] = field(default_factory=list)


class GoldenSetValidator:
    """Golden Set 验证器

    用法:
        validator = GoldenSetValidator(db_manager, docx_dir="./docx")
        result = validator.run_all()
    """

    # 映射: Excel 列名 → DB 列名, 容差
    FIELD_MAP = [
        ("全国综合得分排名", "全国综合得分排名", 0),
        ("综合得分", "综合得分", 0.0001),
        ("阶段增量", "阶段增量", 0.0001),
        ("需求网络优势", "需求网络优势", 0.0001),
        ("能源低碳优势", "能源低碳优势", 0.0001),
        ("约束压力", "约束压力", 0.0001),
        ("综合适宜度", "综合适宜度", 0.0001),
        ("适宜度排名", "适宜度排名", 0),
        ("最终布局类型(V2A口径兼容)", "最终布局类型(V2A口径兼容)", None),
        ("2023国家绿色数据中心数", "2023国家绿色数据中心数", 0),
        ("国家枢纽省份", "国家枢纽省份", None),
        ("2024修正LISA类型", "2024修正LISA类型", None),
        ("内部稳定性标签", "内部稳定性标签", None),
    ]

    def __init__(self, db: DatabaseManager, docx_dir: str | Path = "./docx"):
        self.db = db
        self.docx_dir = Path(docx_dir)

    def run_all(self) -> GoldenTestResult:
        """运行所有 Golden Set 校验"""
        result = GoldenTestResult()

        golden_path = self.docx_dir / "01_系统标准答案_Golden_Set.xlsx"
        if not golden_path.exists():
            result.errors.append(f"Golden Set 文件不存在: {golden_path}")
            return result

        golden_df = pd.read_excel(golden_path, sheet_name="31省最终GoldenSet")

        with self.db.session() as sess:
            for _, excel_row in golden_df.iterrows():
                province = excel_row["省份"]
                db_row = sess.execute(
                    text(f'SELECT * FROM "{TBL_GOLDEN}" WHERE "省份" = :p'),
                    {"p": province},
                ).fetchone()

                if not db_row:
                    result.errors.append(f"省份 '{province}' 在数据库中不存在")
                    result.failed += 1
                    continue

                db_dict = dict(db_row._mapping)

                for excel_col, db_col, tolerance in self.FIELD_MAP:
                    result.total_checks += 1
                    excel_val = excel_row[excel_col]
                    db_val = db_dict.get(db_col)

                    # 处理 NaN
                    if pd.isna(excel_val) and (db_val is None or (isinstance(db_val, float) and pd.isna(db_val))):
                        result.passed += 1
                        continue

                    try:
                        if tolerance is None:
                            ok = str(excel_val).strip() == str(db_val).strip()
                        elif tolerance == 0:
                            ok = int(excel_val) == int(db_val)
                        else:
                            ok = abs(float(excel_val) - float(db_val)) <= tolerance

                        if ok:
                            result.passed += 1
                        else:
                            result.failed += 1
                            detail = {
                                "province": province,
                                "field": db_col,
                                "excel": str(excel_val),
                                "database": str(db_val),
                            }
                            result.details.append(detail)
                            result.errors.append(
                                f"{province}.{db_col}: Excel={excel_val} ≠ DB={db_val}"
                            )
                    except (ValueError, TypeError) as e:
                        result.failed += 1
                        result.errors.append(f"{province}.{db_col}: 比较失败 ({e})")

        return result

    def quick_check(self) -> bool:
        """快速检查: 31 省数量 + 得分排名一致性"""
        golden_path = self.docx_dir / "01_系统标准答案_Golden_Set.xlsx"
        golden_df = pd.read_excel(golden_path, sheet_name="31省最终GoldenSet")

        with self.db.session() as sess:
            db_count = sess.execute(
                text(f'SELECT count(*) FROM "{TBL_GOLDEN}"')
            ).scalar()

            if db_count != 31:
                return False

            # 抽查前 5 名
            for _, row in golden_df.head(5).iterrows():
                db_row = sess.execute(
                    text(f'SELECT "综合得分", "全国综合得分排名" FROM "{TBL_GOLDEN}" WHERE "省份" = :p'),
                    {"p": row["省份"]},
                ).fetchone()
                if not db_row:
                    return False
                db_dict = dict(db_row._mapping)
                if abs(float(db_dict["综合得分"]) - float(row["综合得分"])) > 0.001:
                    return False
                if int(db_dict["全国综合得分排名"]) != int(row["全国综合得分排名"]):
                    return False

        return True
