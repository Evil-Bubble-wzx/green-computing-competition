# 🌱 绿色算力智能决策助手

> **省域绿色算力承载能力评估与资源布局决策支持系统**
>
> 基于 NAT_FINAL 数据（2016–2024，31 省 × 7 维度 × 34 指标），提供智能问答、可视化分析、企划书咨询一站式服务。

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue)](https://www.python.org/)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.61%2B-red)](https://streamlit.io/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-18-336791)](https://www.postgresql.org/)
[![MCP](https://img.shields.io/badge/MCP-2.0-ff6b35)](https://modelcontextprotocol.io/)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)

---

## 📖 目录

- [项目简介](#-项目简介)
- [系统架构](#-系统架构)
- [快速开始](#-快速开始)
- [配置说明](#-配置说明)
- [使用指南](#-使用指南)
- [MCP 工具集](#-mcp-工具集)
- [项目结构](#-项目结构)
- [开发指南](#-开发指南)

---

## 🎯 项目简介

本系统面向 **政府部门、数据中心企业、能源规划机构**，将绿色算力研究成果转化为可交互的智能决策平台。

| 场景 | 做什么 | 面向用户 |
|------|--------|----------|
| 📊 **智能问答** | 自然语言查得分/排名/趋势/布局、对比分析、选址推荐 | 政府 / 研究人员 |
| 📈 **可视化仪表盘** | 6 页交互式 Dashboard，动态图表 + 地图 + 雷达图 | 决策者 / 分析师 |
| 📄 **企划书咨询** | 上传 PDF → 自动解析入库 → AI 结合 NAT_FINAL 数据做可行性分析 | 企业 / 政府 |
| 🔌 **MCP 工具** | 4 个标准化 MCP Server，供 AI 客户端调用 | 开发者 |

### 设计原则

- 🔢 **数值零幻觉**：所有数字来自数据库，LLM 只做翻译和推理，系统提示词 + 后验证双重保障
- 🔍 **全链路可追溯**：每个回答附带来源标注
- 🔌 **可插拔架构**：LLM / Embedding / Reranker / Web Search 四大 Provider，改配置即可切换
- 🗣️ **口径统一**：V2A 布局 / 修正 LISA / SHAP 代理模型 / LPA 潜在类别识别

### 数据口径

- 评估对象: 中国 31 个省级行政区
- 数据年份: 2016–2024
- 指标体系: 7 个一级维度、34 项二级指标
- 五类布局（V2A）: 高适宜综合承载区、需求网络驱动区、能源低碳优势承接区、综合潜力提升区、约束控制区
- 四类 LPA: 高位领先型、优势支撑型、中位追赶型、基础培育型

---

## 🏗 系统架构

```
┌─────────────────────────────────────────────────────────┐
│              AI Client (Claude Desktop / Copilot)         │
├─────────────────────────────────────────────────────────┤
│  mcp-data (8工具) │ mcp-search (3工具) │ mcp-review (3工具) │ mcp-ingest (3工具) │
├─────────────────────────────────────────────────────────┤
│                    ChatEngine                             │
│         分类 → 检索 → RAG → LLM 生成 → 证据验证            │
├─────────────────────────────────────────────────────────┤
│                 HybridSearcher                            │
│   DB (PostgreSQL) + Vector (ChromaDB) — RRF 融合          │
├─────────────────────────────────────────────────────────┤
│                    Data Layer                             │
│  DatabaseManager → QueryEngine (20+ SQL查询)              │
├─────────────────────────────────────────────────────────┤
│              Pluggable Provider Layer                     │
│  LLM: DeepSeek / OpenAI    Embedding: Qwen                │
│  Reranker: LLM / Noop      WebSearch: Builtin / Noop      │
└─────────────────────────────────────────────────────────┘
```

---

## 🚀 快速开始

### 前置条件

- **Python** ≥ 3.10
- **PostgreSQL** 已导入 NAT_FINAL 数据
- **API Keys**：DeepSeek（必需）+ Qwen（必需）

### 1. 安装依赖

```bash
pip install -e ".[dev]"
```

### 2. 配置密钥

编辑 `config/settings.yaml`，或设置环境变量：

```bash
export DEEPSEEK_API_KEY="sk-xxx"
export QWEN_API_KEY="sk-xxx"
```

### 3. 初始化数据库

```bash
python main.py setup
```

### 4. 验证系统

```bash
python main.py evaluate
```

看到 `🎉 系统可交付 — 全部评估通过` 即就绪。

### 5. 启动

```bash
streamlit run src/dashboard/app.py     # 可视化仪表盘
python main.py chat                    # CLI 智能问答
python main.py mcp-data                # MCP 数据查询服务
```

浏览器访问 `http://localhost:8501`。

---

## ⚙ 配置说明

所有配置集中在 `config/settings.yaml`，支持 `${ENV:default}` 环境变量替换（API Key 不入库）。

| 配置段 | 说明 | 默认值 |
|--------|------|--------|
| `llm.provider` | LLM 提供商 | `deepseek` |
| `llm.model` | 模型名称 | `deepseek-v4-flash` |
| `llm.temperature` | 生成温度 | `0.0` |
| `embedding.provider` | 向量化模型 | `qwen`（text-embedding-v3, 1024维） |
| `retrieval.rerank.enabled` | 启用精排 | `true` |
| `chat.strict_numeric_mode` | 数值严格模式 | `true` |
| `ingestion.chunk_size` | PDF 分块大小 | `800` |

### 切换 LLM

```yaml
# config/settings.yaml
llm:
  provider: "openai"
  model: "gpt-4o"
  base_url: "https://api.openai.com/v1"
```

新增 Provider：继承 Base 类 → Factory 注册 → 改配置。详见 [DEV_SPEC.md](DEV_SPEC.md)。

---

## 📘 使用指南

### Dashboard（推荐）

```bash
streamlit run src/dashboard/app.py
```

6 个页面：

| 页面 | 内容 |
|------|------|
| 📊 系统总览 | KPI 卡片 + 排名棒棒糖图 + 布局旭日图 |
| 🏙️ 省份诊断 | 指标卡片 + 七维雷达图（动态范围）+ 历年趋势 |
| 🔄 多省对比 | 对比表 + 雷达叠加 + 趋势叠加（最多 5 省） |
| 🗺️ 空间分析 | Moran 趋势 + 中国地图着色 + LISA 分析 |
| 📐 布局决策 | 五类布局卡片 + 详情 + V2A 规则 |
| 💬 智能问答 | 聊天界面 + 数据查询/企划书咨询双模式 |

**智能问答支持的问题类型**：
- 数据查询："江苏2024年综合得分多少？""贵州七维得分？"
- 对比分析："内蒙古和浙江对比"
- 趋势分析："哪些省份有发展潜力？""北京历年趋势？"
- 选址推荐："哪个省份适合建AI训练中心？""适合建大型数据中心的省份？"

**企划书咨询流程**：切换到「📄 企划书咨询」模式 → 上传 PDF → 系统自动解析入库 → 输入问题即可分析。

### CLI 问答

```bash
python main.py chat
```

输入 `mode` 切换模式，`quit` 退出。

---

## 🔌 MCP 工具集

### Data Query Server（8 工具）

```bash
python main.py mcp-data
```

| 工具 | 功能 |
|------|------|
| `list_provinces` | 列出 31 省 |
| `query_province_score` | 查省份得分/排名/布局/LPA |
| `compare_provinces` | 多省对比 |
| `get_trend` | 历年趋势（2016–2024） |
| `query_layout` | 五类布局查询 |
| `get_dimensions` | 七维得分 |
| `get_boundary_provinces` | 边界省份 |
| `get_ranking` | Top N 排名 |

### Search Server（3 工具）

```bash
python main.py mcp-search
```

| 工具 | 功能 |
|------|------|
| `search` | 混合检索（DB + Vector） |
| `search_db` | 仅数据库检索 |
| `search_web` | 联网搜索 |

### Ingestion Server（3 工具）

```bash
python main.py mcp-ingest
```

| 工具 | 功能 |
|------|------|
| `ingest_document` | 摄入 PDF（解析→分块→向量化） |
| `list_documents` | 列出已摄入文档 |
| `delete_document` | 删除文档 |

### Review Server（3 工具）

```bash
python main.py mcp-review
```

| 工具 | 功能 |
|------|------|
| `generate_report` | 生成企划书分析报告 |
| `review_report` | MiniMax 评审报告 |
| `auto_revise` | 自动循环修改至 ≥ 8 分 |

---

## 🤖 Claude Code Skills

项目内置 5 个 Claude Code 技能，自动触发：

| 技能 | 触发词 | 功能 |
|------|--------|------|
| **dev-guide** | 开发规范、coding rules、帮我写代码 | 强制执行项目开发规范：配置驱动、Factory 模式、Prompt 纪律、Golden Set 完整性 |
| **data-guardian** | 数据校验、guardian、幻觉检查 | 验证回答数值来源 NAT_FINAL、术语合规（LISA/SHAP/LPA）、证据可追溯 |
| **system-validator** | 验证系统、系统检查、validate system | 一键检查 7 项系统健康指标：数据库→Golden Set→模块→API→Prompt→MCP→Dashboard |
| **proposal-pipeline** | 分析企划书、full pipeline | PDF 摄入→DB+Vector 检索→ChatEngine 分析→可选 MiniMax 评审循环 |
| **review-loop** | 评审循环、auto revise | DeepSeek 生成→MiniMax-M3 5维评分→循环修改至 ≥8 分 |

技能文件：`.claude/skills/*/SKILL.md`

---

## 📁 项目结构

```
green-computing-competition/
├── main.py                          # 主入口（setup / chat / mcp-* / evaluate）
├── pyproject.toml                   # 项目配置 + 依赖
├── README.md
├── DEV_SPEC.md                      # 开发规格文档
│
├── config/
│   └── settings.yaml                # 全局配置
│
├── src/
│   ├── core/                        # 类型 / 配置 / 异常
│   │   ├── types.py                 # 7 个 Enum + 8 个 dataclass
│   │   ├── settings.py              # YAML 加载 + ${ENV} 替换
│   │   └── exceptions.py            # 分层异常体系
│   │
│   ├── data/                        # 数据层
│   │   ├── database.py              # PostgreSQL 连接池管理
│   │   ├── models.py                # SQLAlchemy ORM
│   │   ├── loader.py                # Excel → DB 导入
│   │   └── queries.py               # 纯 SQL 查询引擎（20+ 方法）
│   │
│   ├── libs/                        # 可插拔 Provider 层
│   │   ├── llm/                     # LLM（DeepSeek / OpenAI）
│   │   ├── embedding/               # Embedding（Qwen）
│   │   ├── reranker/                # Reranker（LLM / Noop）
│   │   └── search/                  # Web Search（Builtin / Noop）
│   │
│   ├── ingestion/                   # PDF 摄入管线
│   │   ├── pdf_parser.py
│   │   ├── chunker.py
│   │   ├── vector_store.py          # ChromaDB 封装
│   │   └── pipeline.py              # PDF → Chunk → Embed → DB
│   │
│   ├── retrieval/
│   │   └── hybrid_search.py         # DB + Vector → RRF → Rerank
│   │
│   ├── chat/                        # 智能问答引擎
│   │   ├── engine.py                # 分类 → 检索 → 生成 → 验证
│   │   └── prompts.py               # 系统提示词
│   │
│   ├── review/                      # 报告生成 + 评审
│   │   ├── report_generator.py
│   │   └── minimax_reviewer.py
│   │
│   ├── evaluation/                  # 系统评估
│   │   ├── runner.py
│   │   ├── golden_test.py
│   │   └── qa_quality.py
│   │
│   ├── mcp_servers/                 # 4 个 MCP Server
│   │   ├── data_query/              # 8 工具
│   │   ├── search/                  # 3 工具
│   │   ├── ingestion/               # 3 工具
│   │   └── review/                  # 3 工具
│   │
│   └── dashboard/                   # Streamlit 仪表盘
│       ├── app.py                   # 入口 + 路由
│       ├── styles.py                # 全局 CSS
│       ├── data_loader.py           # 缓存数据加载
│       ├── components/
│       │   └── charts.py            # Plotly 图表组件
│       └── pages/                   # 6 个页面
│           ├── overview.py          # 系统总览
│           ├── province.py          # 省份诊断
│           ├── comparison.py        # 多省对比
│           ├── spatial.py           # 空间分析
│           ├── layout_page.py       # 布局决策
│           └── chat_page.py         # 智能问答
│
├── scripts/
│   └── import_all.py                # Excel → PostgreSQL 全量导入
│
├── tests/
│   └── conftest.py                  # pytest fixtures
│
├── data/
│   ├── china_provinces.geojson      # 中国省份 GeoJSON
│   ├── db/chroma/                   # ChromaDB 向量数据
│   └── reports/                     # 企划书报告输出
│
└── logs/                            # 系统日志
```

---

## 🛠 开发指南

### 运行测试

```bash
python main.py evaluate    # 系统级评估（Golden Set + QA + 性能）
pytest tests/              # 单元测试
```

### 代码质量

```bash
ruff check src/
ruff format src/
```

### 项目约定

- 所有 LLM/Embedding 调用走 `openai.OpenAI()` 统一接口
- 数据问答必须从 `QueryEngine` 获取数字，严禁 LLM 编造
- 术语规范见 `src/chat/prompts.py`
- 修改数据后必须运行 `python main.py evaluate` 验证 Golden Set 一致性

---

## 📄 License

MIT © Green Computing Team

---

> 💡 开发规格详见 [DEV_SPEC.md](DEV_SPEC.md)。
