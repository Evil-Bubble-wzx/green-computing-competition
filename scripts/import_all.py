"""
NAT_FINAL 全量数据导入脚本

把 docx/ 下所有 Excel 的每个 sheet 导入 PostgreSQL。
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import re
import pandas as pd
from sqlalchemy import create_engine, text

from src.core.settings import load_settings


def safe_name(name: str) -> str:
    """清理表名/列名"""
    name = str(name).strip()
    name = name.replace(" ", "_").replace("（", "(").replace("）", ")")
    name = re.sub(r"[^\w一-鿿()\-\.\+]", "_", name)
    return name[:63]


def main():
    settings = load_settings("config/settings.yaml")
    cfg = settings.data.database
    db_url = f"postgresql://{cfg.user}:{cfg.password}@{cfg.host}:{cfg.port}/{cfg.database}"
    engine = create_engine(db_url, echo=False)

    docx_dir = Path(settings.data.docx_dir)

    # 跳过临时文件 (Office 锁文件)
    files = [f for f in sorted(docx_dir.glob("*.xlsx")) if not f.name.startswith(".~")]
    total_rows = 0
    total_sheets = 0

    print("=" * 60)
    print("  NAT_FINAL 全量数据导入 PostgreSQL")
    print(f"  数据库: {cfg.host}:{cfg.port}/{cfg.database}")
    print("=" * 60)

    for fp in files:
        prefix = safe_name(fp.stem[:30])
        try:
            xls = pd.ExcelFile(fp, engine="openpyxl")
        except Exception as e:
            print(f"\n📄 {fp.name}  ⚠️ 无法打开 ({e})")
            continue

        print(f"\n📄 {fp.name}  ({len(xls.sheet_names)} sheets)")

        for sname in xls.sheet_names:
            try:
                # 先读前 2 行判断有无表头
                peek = pd.read_excel(xls, sheet_name=sname, header=None, nrows=2)
                if peek.empty:
                    continue

                # 判断第一行是否像表头（有字符串混杂）
                row0 = peek.iloc[0].astype(str).tolist()
                row1 = peek.iloc[1].astype(str).tolist()
                # 如果第一行全是 "0,1,2..." 数字，说明无表头
                looks_numeric = all(
                    v.replace(".", "").replace("-", "").replace("e", "").isdigit()
                    or v in ("nan", "None", "")
                    for v in row0
                )
                if looks_numeric and not all(
                    v.replace(".", "").replace("-", "").replace("e", "").isdigit()
                    or v in ("nan", "None", "")
                    for v in row1
                ):
                    # 第一行数字、第二行有文字 → 无表头
                    df = pd.read_excel(xls, sheet_name=sname, header=None)
                    df.columns = [f"col_{i+1}" for i in range(len(df.columns))]
                else:
                    df = pd.read_excel(xls, sheet_name=sname, header=0)

                # 清理列名
                df = df.copy()
                df.columns = [safe_name(c) for c in df.columns]
                df = df.dropna(how="all").dropna(axis=1, how="all")
                if df.empty:
                    continue

                table_name = safe_name(f"{prefix}_{sname}")

                # 写入 PG
                df.to_sql(table_name, engine, if_exists="replace", index=False)
                n = len(df)
                total_rows += n
                total_sheets += 1
                col_preview = ", ".join(df.columns[:6])
                if len(df.columns) > 6:
                    col_preview += " ..."
                print(f"   ✓ {table_name}  → {n}行 × {len(df.columns)}列")

            except Exception as e:
                print(f"   ✗ {sname}: {type(e).__name__}: {str(e)[:80]}")

    # 总结
    print(f"\n{'=' * 60}")
    print(f"  导入完成: {total_sheets} 张表, {total_rows} 行")
    print(f"{'=' * 60}")

    # 列出所有表
    print("\n📋 数据库表清单:")
    with engine.connect() as conn:
        tables = pd.read_sql_query(
            "SELECT tablename FROM pg_catalog.pg_tables "
            "WHERE schemaname='public' ORDER BY tablename",
            conn,
        )
        for t in tables["tablename"]:
            cnt = conn.execute(text(f'SELECT COUNT(*) FROM "public"."{t}"')).scalar()
            cols = pd.read_sql_query(
                f"SELECT column_name FROM information_schema.columns "
                f"WHERE table_name='{t}' ORDER BY ordinal_position",
                conn,
            )
            cn = ", ".join(cols["column_name"].tolist()[:8])
            if len(cols) > 8:
                cn += " ..."
            print(f"   {t}  ({cnt}行)  [{cn}]")

    engine.dispose()


if __name__ == "__main__":
    main()
