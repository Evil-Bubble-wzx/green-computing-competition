"""
绿色算力智能决策助手 - 主入口

支持三种运行模式:
  1. setup    - 初始化数据库，导入 NAT_FINAL 数据
  2. chat     - 启动智能问答 (CLI 交互)
  3. web      - 启动 Streamlit Dashboard
  4. mcp      - 启动 MCP Server
"""

import sys
from pathlib import Path

# 确保项目根目录在 sys.path 中
PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))


def cmd_setup(settings) -> int:
    """
    初始化系统: 创建数据库并导入 NAT_FINAL 数据。

    步骤:
      1. 连接 PostgreSQL 并创建表
      2. 导入 Golden Set、综合得分、七维得分、指标字典、LPA 类型
      3. 运行 Golden Set 一致性验证
    """
    from src.data.database import DatabaseManager
    from src.data.loader import DataLoader

    print("=" * 60)
    print("  绿色算力智能决策助手 - 系统初始化")
    print("=" * 60)
    print()

    # 1. 初始化数据库
    db = DatabaseManager(settings)
    print(f"[1/4] 连接 PostgreSQL: {db.db_url}")
    db.initialize()
    print("  ✓ 数据库表已创建")

    # 2. 导入数据
    print(f"\n[2/4] 导入 NAT_FINAL 数据...")
    loader = DataLoader(db, docx_dir=settings.data.docx_dir)
    counts = loader.load_all()

    for table, count in counts.items():
        print(f"  ✓ {table}: {count} 条记录")

    # 3. 验证
    print(f"\n[3/4] 验证 Golden Set 一致性...")
    issues = loader.verify_golden()
    if issues:
        print("  ✗ 发现问题:")
        for issue in issues:
            print(f"    - {issue}")
    else:
        print("  ✓ Golden Set 验证通过 (31省完整)")

    # 4. 完成
    print(f"\n[4/4] 系统初始化完成")
    print(f"  数据版本: NAT_FINAL")
    print(f"  数据库: {db.db_url}")
    return 0


def cmd_chat(settings) -> int:
    """
    启动 CLI 交互式问答。

    用法: python main.py chat
    """
    from src.data.database import DatabaseManager
    from src.data.queries import QueryEngine
    from src.libs.llm.llm_factory import LLMFactory
    from src.retrieval.hybrid_search import HybridSearcher
    from src.chat.engine import ChatEngine

    print("=" * 60)
    print("  绿色算力智能决策助手 - 智能问答 (CLI)")
    print("=" * 60)
    print()

    # 初始化
    db = DatabaseManager(settings)
    qe = QueryEngine(db)
    llm = LLMFactory.create(settings)
    searcher = HybridSearcher(query_engine=qe)
    engine = ChatEngine(llm, searcher)

    print("可用模式:")
    print("  1  - 数据查询（查省份、得分、排名、趋势...）")
    print("  2  - 企划书咨询（上传 PDF 后分析）")
    print()
    print("输入 'quit' 退出，'mode' 切换模式。")
    print()

    # 默认模式
    current_mode = "data_query"
    mode_labels = {"data_query": "📊 数据查询", "proposal_consult": "📄 企划书咨询"}

    while True:
        try:
            user_input = input(f"\n[{mode_labels[current_mode]}] 你: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n已退出。")
            break

        if not user_input:
            continue

        if user_input.lower() == "quit":
            print("已退出。")
            break

        if user_input.lower() == "mode":
            current_mode = "proposal_consult" if current_mode == "data_query" else "data_query"
            print(f"已切换到: {mode_labels[current_mode]}")
            continue

        # 调用引擎
        print("思考中...", end="\r")
        try:
            resp = engine.chat(user_input, mode=current_mode)
            print(f"[{mode_labels[current_mode]}] 助手: {resp.answer}")
            if resp.disclaimer:
                print(f"  ⚠️  {resp.disclaimer}")
        except Exception as e:
            print(f"  ❌ 出错: {e}")

    db.close()
    return 0


def cmd_web(settings) -> int:
    """启动 Streamlit Dashboard"""
    import subprocess
    dashboard = PROJECT_ROOT / "src" / "dashboard" / "app.py"
    subprocess.run(["streamlit", "run", str(dashboard)])
    return 0


def cmd_mcp_data(settings) -> int:
    """启动 Data Query MCP Server"""
    from src.mcp_servers.data_query.server import main as mcp_main
    return mcp_main()


def cmd_mcp_ingest(settings) -> int:
    """启动 Ingestion MCP Server"""
    from src.mcp_servers.ingestion.server import main as mcp_main
    return mcp_main()


def cmd_mcp_search(settings) -> int:
    """启动 Search MCP Server"""
    from src.mcp_servers.search.server import main as mcp_main
    return mcp_main()


def cmd_evaluate(settings) -> int:
    """运行系统评估"""
    from src.evaluation.runner import run_all
    return run_all()


def cmd_mcp_review(settings) -> int:
    """启动 Review MCP Server"""
    from src.mcp_servers.review.server import main as mcp_main
    return mcp_main()


def main() -> int:
    """
    主入口函数。

    Returns:
        int: 退出码 (0 = 成功)
    """
    from src.core.settings import SettingsError, load_settings

    # 加载配置
    config_path = Path("config/settings.yaml")
    try:
        settings = load_settings(config_path)
    except SettingsError as exc:
        print(f"[ERROR] 配置加载失败: {exc}", file=sys.stderr)
        return 1

    # 解析子命令
    if len(sys.argv) < 2:
        print("用法: python main.py <command>")
        print()
        print("可用命令:")
        print("  setup       - 初始化数据库，导入 NAT_FINAL 数据")
        print("  chat        - 启动 CLI 智能问答")
        print("  web         - 启动 Streamlit Dashboard")
        print("  mcp-data    - 启动 Data Query MCP Server")
        print("  mcp-search  - 启动 Search MCP Server")
        print("  mcp-review  - 启动 Review MCP Server")
        print("  mcp-ingest  - 启动 Ingestion MCP Server")
        print("  evaluate    - 运行系统评估 (Golden Set + QA + 性能)")
        print()
        return 1

    command = sys.argv[1].lower()

    commands = {
        "setup": cmd_setup,
        "chat": cmd_chat,
        "web": cmd_web,
        "mcp-data": cmd_mcp_data,
        "mcp-review": cmd_mcp_review,
        "mcp-search": cmd_mcp_search,
        "evaluate": cmd_evaluate,
        "mcp-ingest": cmd_mcp_ingest,
    }

    if command not in commands:
        print(f"[ERROR] 未知命令: {command}", file=sys.stderr)
        print(f"可用命令: {', '.join(commands.keys())}")
        return 1

    try:
        return commands[command](settings)
    except KeyboardInterrupt:
        print("\n\n已退出。")
        return 0
    except Exception as exc:
        print(f"\n[ERROR] {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
