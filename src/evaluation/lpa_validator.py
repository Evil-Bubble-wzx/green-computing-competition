"""
稳定性标签与 LPA 交叉验证 (H1-B)

五项检查（每项 31 省，共 155 项）：
  1. LPA 类型命名        — DB TBL_LPA  vs NAT_FINAL"LPA省份归属"
  2. 布局稳定性标签       — DB TBL_GOLDEN vs 布局权威(03)
  3. 保持原布局概率       — DB TBL_GOLDEN vs 布局权威(03)
  4. LPA 稳定性标签       — DB TBL_LPA  vs LPA 权威(02)
  5. LPA 基准类型保持率   — DB TBL_LPA  vs LPA 权威(02)

权威数据源:
  - docx/03_布局边界省份与稳定性标签.xlsx → 边界省份 (布局门控，边界型=四川/陕西/安徽 3省)
  - docx/02_LPA稳定性与边界省份.xlsx → 省份Bootstrap稳定性 (LPA类型，边界型=6省)

⚠️ 口径区分（重要）:
  - "内部稳定性标签"(Golden Set) = 布局门控稳定性，边界型 = 四川/陕西/安徽 (3省)
  - "内部稳定性标签"(TBL_LPA)     = LPA 类型稳定性，边界型 = 宁夏/上海/四川/山东/青海/湖南 (6省)
  二者不可混用。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd
from sqlalchemy import text

from src.data.database import DatabaseManager
from src.data.queries import TBL_LPA, TBL_GOLDEN

# ---------------------------------------------------------------------------
# 有效值集合
# ---------------------------------------------------------------------------

VALID_LPA_TYPES = {"高位领先型", "优势支撑型", "中位追赶型", "基础培育型"}
VALID_STABILITY_LABELS = {"高稳定", "中稳定", "边界型"}


@dataclass
class LPAValidationResult:
    """验证结果"""
    total_checks: int = 0
    passed: int = 0
    failed: int = 0
    details: list[dict] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


class LPAValidator:
    """稳定性标签与 LPA 交叉验证器

    对 31 省逐省验证：
      1. LPA 类型命名   — DB TBL_LPA  vs NAT_FINAL"LPA省份归属"
      2. 稳定性标签      — DB TBL_GOLDEN vs 布局权威(03)
      3. 保持原布局概率  — DB TBL_GOLDEN vs 布局权威(03)

    用法:
        validator = LPAValidator(db_manager, docx_dir="./docx")
        result = validator.run_all()
    """

    def __init__(self, db: DatabaseManager, docx_dir: str | Path = "./docx"):
        self.db = db
        self.docx_dir = Path(docx_dir)

    # ------------------------------------------------------------------
    # 主入口
    # ------------------------------------------------------------------

    def run_all(self) -> LPAValidationResult:
        result = LPAValidationResult()

        try:
            lpa_excel = self._load_lpa_excel()
            layout_excel = self._load_layout_excel()
            bootstrap_excel = self._load_bootstrap_excel()
        except FileNotFoundError as e:
            result.errors.append(f"Excel 文件缺失: {e}")
            return result
        except Exception as e:
            result.errors.append(f"Excel 读取失败: {e}")
            return result

        provinces = lpa_excel["省份"].tolist()
        if len(provinces) != 31:
            result.errors.append(f"LPA Excel 省份数量: {len(provinces)} (期望 31)")

        for _, row in lpa_excel.iterrows():
            province = row["省份"]

            layout_row = layout_excel[layout_excel["省份"] == province]
            layout_row = layout_row.iloc[0] if len(layout_row) > 0 else None

            boot_row = bootstrap_excel[bootstrap_excel["省份"] == province]
            boot_row = boot_row.iloc[0] if len(boot_row) > 0 else None

            # --- 检查 1: LPA 类型命名 ---
            result.total_checks += 1
            self._check_lpa_type(result, province, row)

            # --- 检查 2: 布局稳定性标签 (布局门控) ---
            result.total_checks += 1
            self._check_stability_label(result, province, layout_row)

            # --- 检查 3: 保持原布局概率 ---
            result.total_checks += 1
            self._check_keep_prob(result, province, layout_row)

            # --- 检查 4: LPA 稳定性标签 (LPA 类型 Bootstrap) ---
            result.total_checks += 1
            self._check_lpa_stability_label(result, province, boot_row)

            # --- 检查 5: LPA 基准类型保持率 ---
            result.total_checks += 1
            self._check_lpa_keep_rate(result, province, boot_row)

        return result

    # ------------------------------------------------------------------
    # 检查 1: LPA 类型命名
    # ------------------------------------------------------------------

    def _check_lpa_type(self, result: LPAValidationResult,
                        province: str, excel_row: pd.Series) -> bool:
        """DB TBL_LPA.类型命名 vs NAT_FINAL LPA省份归属.类型命名"""
        excel_type = str(excel_row.get("类型命名", "")).strip()

        with self.db.session() as sess:
            db_row = sess.execute(
                text(f'SELECT "类型命名" FROM "{TBL_LPA}" WHERE "省份" = :p'),
                {"p": province},
            ).fetchone()

        if not db_row:
            result.failed += 1
            result.errors.append(f"{province}.LPA类型命名: DB中缺失")
            return False

        db_type = str(db_row[0]).strip() if db_row[0] else ""

        if excel_type != db_type:
            result.failed += 1
            result.errors.append(f"{province}.LPA类型命名: Excel={excel_type} ≠ DB={db_type}")
            return False

        if excel_type not in VALID_LPA_TYPES:
            result.failed += 1
            result.errors.append(f"{province}.LPA类型命名: 无效值 '{excel_type}'")
            return False

        result.passed += 1
        return True

    # ------------------------------------------------------------------
    # 检查 2: 稳定性标签 (布局门控)
    # ------------------------------------------------------------------

    def _check_stability_label(self, result: LPAValidationResult,
                               province: str, layout_row) -> bool:
        """DB TBL_GOLDEN.内部稳定性标签 vs 布局权威(03).内部稳定性标签"""
        if layout_row is None:
            result.failed += 1
            result.errors.append(f"{province}.稳定性标签: 布局权威(03)中无此省份")
            return False

        ref_label = str(layout_row.get("内部稳定性标签", "")).strip()

        with self.db.session() as sess:
            db_row = sess.execute(
                text(f'SELECT "内部稳定性标签" FROM "{TBL_GOLDEN}" WHERE "省份" = :p'),
                {"p": province},
            ).fetchone()

        if not db_row:
            result.failed += 1
            result.errors.append(f"{province}.稳定性标签: DB Golden Set 中缺失")
            return False

        db_label = str(db_row[0]).strip() if db_row[0] else ""

        if ref_label != db_label:
            result.failed += 1
            result.errors.append(f"{province}.稳定性标签: 权威={ref_label} ≠ DB={db_label}")
            return False

        if ref_label not in VALID_STABILITY_LABELS:
            result.failed += 1
            result.errors.append(f"{province}.稳定性标签: 无效值 '{ref_label}'")
            return False

        result.passed += 1
        return True

    # ------------------------------------------------------------------
    # 检查 3: 保持原布局概率
    # ------------------------------------------------------------------

    def _check_keep_prob(self, result: LPAValidationResult,
                         province: str, layout_row) -> bool:
        """DB TBL_GOLDEN.保持原布局概率 vs 布局权威(03).保持原布局概率"""
        if layout_row is None:
            result.failed += 1
            result.errors.append(f"{province}.保持原布局概率: 布局权威(03)中无此省份")
            return False

        ref_prob = float(layout_row.get("保持原布局概率", 0.0))

        with self.db.session() as sess:
            db_row = sess.execute(
                text(f'SELECT "保持原布局概率" FROM "{TBL_GOLDEN}" WHERE "省份" = :p'),
                {"p": province},
            ).fetchone()

        if not db_row:
            result.failed += 1
            result.errors.append(f"{province}.保持原布局概率: DB Golden Set 中缺失")
            return False

        db_prob = float(db_row[0]) if db_row[0] else 0.0

        if abs(ref_prob - db_prob) > 0.0001:
            result.failed += 1
            result.errors.append(
                f"{province}.保持原布局概率: 权威={ref_prob:.4f} ≠ DB={db_prob:.4f}"
            )
            return False

        result.passed += 1
        return True

    # ------------------------------------------------------------------
    # Excel 加载
    # ------------------------------------------------------------------

    def _load_lpa_excel(self) -> pd.DataFrame:
        path = self.docx_dir / "05_综合评价核心结果_NAT_FINAL.xlsx"
        if not path.exists():
            raise FileNotFoundError(str(path))
        df = pd.read_excel(path, sheet_name="LPA省份归属")
        required = ["省份", "类型命名"]
        for col in required:
            if col not in df.columns:
                raise ValueError(f"LPA省份归属 sheet 缺少列: {col}")
        return df

    def _load_layout_excel(self) -> pd.DataFrame:
        """加载布局门控稳定性权威数据 (03)"""
        path = self.docx_dir / "03_布局边界省份与稳定性标签.xlsx"
        if not path.exists():
            raise FileNotFoundError(str(path))
        df = pd.read_excel(path, sheet_name="边界省份")
        required = ["省份", "保持原布局概率", "内部稳定性标签"]
        for col in required:
            if col not in df.columns:
                raise ValueError(f"边界省份 sheet 缺少列: {col}")
        return df

    def _load_bootstrap_excel(self) -> pd.DataFrame:
        """加载 LPA 类型稳定性权威数据 (02)"""
        path = self.docx_dir / "02_LPA稳定性与边界省份.xlsx"
        if not path.exists():
            raise FileNotFoundError(str(path))
        df = pd.read_excel(path, sheet_name="省份Bootstrap稳定性")
        required = ["省份", "基准类型保持率", "内部稳定性标签"]
        for col in required:
            if col not in df.columns:
                raise ValueError(f"省份Bootstrap稳定性 sheet 缺少列: {col}")
        return df

    # ------------------------------------------------------------------
    # 检查 4/5: LPA 类型稳定性 (Bootstrap 口径)
    # ------------------------------------------------------------------

    def _check_lpa_stability_label(self, result: LPAValidationResult,
                                   province: str, boot_row) -> bool:
        """DB TBL_LPA.内部稳定性标签 vs 权威(02).内部稳定性标签"""
        if boot_row is None:
            result.failed += 1
            result.errors.append(f"{province}.LPA稳定性标签: 权威(02)中无此省份")
            return False

        ref_label = str(boot_row.get("内部稳定性标签", "")).strip()

        with self.db.session() as sess:
            db_row = sess.execute(
                text(f'SELECT "内部稳定性标签" FROM "{TBL_LPA}" WHERE "省份" = :p'),
                {"p": province},
            ).fetchone()

        if not db_row:
            result.failed += 1
            result.errors.append(f"{province}.LPA稳定性标签: DB TBL_LPA 中缺失")
            return False

        db_label = str(db_row[0]).strip() if db_row[0] else ""

        if ref_label != db_label:
            result.failed += 1
            result.errors.append(f"{province}.LPA稳定性标签: 权威={ref_label} ≠ DB={db_label}")
            return False

        if ref_label not in VALID_STABILITY_LABELS:
            result.failed += 1
            result.errors.append(f"{province}.LPA稳定性标签: 无效值 '{ref_label}'")
            return False

        result.passed += 1
        return True

    def _check_lpa_keep_rate(self, result: LPAValidationResult,
                             province: str, boot_row) -> bool:
        """DB TBL_LPA.基准类型保持率 vs 权威(02).基准类型保持率"""
        if boot_row is None:
            result.failed += 1
            result.errors.append(f"{province}.LPA基准类型保持率: 权威(02)中无此省份")
            return False

        ref_rate = float(boot_row.get("基准类型保持率", 0.0))

        with self.db.session() as sess:
            db_row = sess.execute(
                text(f'SELECT "基准类型保持率" FROM "{TBL_LPA}" WHERE "省份" = :p'),
                {"p": province},
            ).fetchone()

        if not db_row:
            result.failed += 1
            result.errors.append(f"{province}.LPA基准类型保持率: DB TBL_LPA 中缺失")
            return False

        db_rate = float(db_row[0]) if db_row[0] else 0.0

        if abs(ref_rate - db_rate) > 0.0001:
            result.failed += 1
            result.errors.append(
                f"{province}.LPA基准类型保持率: 权威={ref_rate:.4f} ≠ DB={db_rate:.4f}"
            )
            return False

        result.passed += 1
        return True
