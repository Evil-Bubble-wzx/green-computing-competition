# DEV_SPEC — 绿色算力智能决策助手 开发规格文档

> 版本: v1.0.0 | 更新: 2026-08-11 | 数据基准: NAT_FINAL

---

## 一、项目目标

将"绿色算力论文+Excel数据"升级为**可交互的智能决策支持系统**，实现:

1. **数据可视化**: 6 页交互式 Streamlit Dashboard，动态图表 + 地图 + 雷达图
2. **智能问答**: RAG 架构，支持查数据、做对比、趋势分析、选址推荐
3. **企划书咨询**: PDF 上传 → 自动摄入 → 结合 NAT_FINAL 数据做可行性分析
4. **MCP 工具暴露**: 4 个标准化 MCP Server 供 AI 客户端调用

## 二、技术选型

| 层面 | 选型 | 说明 |
|------|------|------|
| LLM 调用 | **OpenAI SDK** (`openai>=1.0`) | 统一接口，DeepSeek/Qwen/OpenAI 均通过 `openai.OpenAI()` 调用 |
| 数据库 | **PostgreSQL** + SQLAlchemy | 连接池、pool_pre_ping |
| 向量存储 | ChromaDB | 企划书 PDF 语义搜索 |
| 可视化 | Streamlit + Plotly | `st.navigation` 原生多页，动态雷达图 |
| 配置 | YAML + `${ENV:default}` | 环境变量替换，API Key 不入库 |
| MCP | mcp>=1.0 | stdio transport |

## 三、系统架构

```
┌─────────────────────────────────────────────────────────┐
│              AI Client (Claude Desktop / Copilot)         │
├─────────────────────────────────────────────────────────┤
│  mcp-data (8) │ mcp-search (3) │ mcp-ingest (3) │ mcp-review (3) │
├─────────────────────────────────────────────────────────┤
│                    ChatEngine                             │
│         分类 → 检索 → RAG → LLM 生成 → 证据验证            │
├─────────────────────────────────────────────────────────┤
│                 HybridSearcher                            │
│   DB (PostgreSQL) + Vector (ChromaDB+Embedding)           │
│            RRF Fusion → LLM Reranker                      │
├─────────────────────────────────────────────────────────┤
│                    Data Layer                             │
│  DatabaseManager → QueryEngine (20+ SQL查询)              │
│  DataLoader (Excel→DB) + GoldenSetValidator               │
├─────────────────────────────────────────────────────────┤
│              Pluggable Provider Layer                     │
│  LLM: DeepSeek / OpenAI    Embedding: Qwen                │
│  Reranker: LLM / Noop      WebSearch: Builtin / Noop      │
└─────────────────────────────────────────────────────────┘
```

## 四、开发阶段总览 (9 个 Phase)

| 阶段 | 内容 | 优先级 | 状态 |
|------|------|--------|------|
| **A** | 工程骨架与数据层 | ⭐⭐⭐ | ✅ 完成 |
| **B** | 可插拔 RAG Provider 层 | ⭐⭐⭐ | ✅ 完成 |
| **C** | PDF 企划书摄入管线 | ⭐⭐ | ✅ 完成 |
| **D** | 混合检索引擎 | ⭐⭐⭐ | ✅ 完成 |
| **E** | 智能问答引擎 | ⭐⭐⭐ | ✅ 完成 |
| **F** | MCP Server (四个) | ⭐⭐ | ✅ 完成 |
| **G** | 可视化仪表盘 | ⭐⭐ | ✅ 完成 |
| **H** | 评估体系与 E2E | ⭐⭐ | ✅ 完成 |
| **I** | 企划书评审 | ⭐ | ✅ 完成 |

---

## Phase A: 工程骨架与数据层 ✅

### A1 - 项目结构初始化 ✅
- [x] 目录结构
- [x] pyproject.toml
- [x] config/settings.yaml (PostgreSQL, LLM, Embedding, Rerank, Vector, Ingestion, Chat, Dashboard, MCP)
- [x] main.py (setup / chat / web / mcp-data / mcp-search / mcp-ingest / mcp-review / evaluate)

### A2 - 核心类型与配置 ✅
- [x] `src/core/types.py` — 7 个 dataclass + 6 个 Enum
- [x] `src/core/settings.py` — YAML 加载 + `${ENV:default}` 环境变量替换
- [x] `src/core/exceptions.py` — 分层异常体系

### A3 - 数据层 ✅
- [x] `src/data/database.py` — DatabaseManager (SQLAlchemy + PostgreSQL, 连接池)
- [x] `src/data/models.py` — 6 张 ORM 表
- [x] `src/data/loader.py` — DataLoader (Excel→PostgreSQL + Golden Set 一致性验证)
- [x] `src/data/queries.py` — QueryEngine (20+ 查询方法)

---

## Phase B: 可插拔 RAG Provider 层 ✅

每层 Provider 遵循 **Base → Implementation → Factory** 三件套。

### 已注册 Provider

| 层 | 已注册 | 切换方式 |
|---|---|---|
| LLM | `deepseek`, `openai` | `llm.provider` |
| Embedding | `qwen` | `embedding.provider` |
| Reranker | `llm`, `none` | `retrieval.rerank.provider` |
| Web Search | `builtin`, `none` | `web_search.provider` |

### 新增 Provider 三步
1. 继承 Base 类 → 实现核心方法
2. 在 Factory 的 `_register_providers()` 中注册
3. `config/settings.yaml` 切换 `provider`

---

## Phase C: PDF 企划书摄入管线 ✅

- [x] `src/ingestion/pdf_parser.py` — pdfplumber 文本 + 表格提取
- [x] `src/ingestion/chunker.py` — RecursiveCharTextSplitter 中文分块
- [x] `src/ingestion/vector_store.py` — ChromaDB 封装（add/search/delete/list）
- [x] `src/ingestion/pipeline.py` — 编排: PDF→Chunk→Embed→ChromaDB

---

## Phase D: 混合检索引擎 ✅

### D1 - 关键词→SQL 映射 ✅
- [x] `src/retrieval/hybrid_search.py` — HybridSearcher
- [x] 10 种查询模式自动识别
- [x] 省份名 + 年份正则自动提取
- [x] 泛问兜底：无匹配时自动返回 Top10 排名 + 布局汇总 + 边界省份

### D2 - 向量检索 ✅
- [x] Qwen Embedding → ChromaDB 语义搜索，已接入 HybridSearcher
- [x] 企划书咨询模式下 DB + Vector 双通道检索

### D3 - RRF 融合 ✅
- [x] 多通道去重 + 分数排序
- [x] LLMReranker 精排（可选）

---

## Phase E: 智能问答引擎 ✅

### E1 - 问题分类 ✅
- [x] 城市级越界检测（仅拦截明确指定城市名的精确排名查询）
- [x] 趋势/推荐/对比类问题全部放行给 LLM 处理

### E2 - Prompt 构建 ✅
- [x] `src/chat/prompts.py` — DATA_QUERY + PROPOSAL_CONSULT 双模式系统提示词
- [x] 数据查询：支持查数据、做对比、趋势分析、选址推荐
- [x] 企划书咨询：关键字段提取 + 逐维分析 + 匹配度评分
- [x] 术语规范表（LISA/SHAP/LPA/枢纽节点）
- [x] 3 类示例（查数据/做推荐/趋势分析）

### E3 - 回答生成与验证 ✅
- [x] DeepSeek LLM 生成
- [x] 数值来源追溯（_extract_evidence）
- [x] 孤儿数字自动警告

### E4 - CLI + Streamlit 双入口 ✅
- [x] `python main.py chat` — CLI 交互
- [x] Dashboard 聊天页 — PDF 上传 + 双模式切换
- [x] ChatEngine 缓存复用（st.cache_resource）

---

## Phase F: MCP Server 实现 ✅

### F1 - Data Query MCP Server ✅
- [x] `src/mcp_servers/data_query/` — 8 工具
- [x] MCP SDK v2.0, stdio transport

### F2 - Search MCP Server ✅
- [x] `src/mcp_servers/search/` — 3 工具 (search, search_db, search_web)

### F3 - Ingestion MCP Server ✅
- [x] `src/mcp_servers/ingestion/` — 3 工具 (ingest_document, list_documents, delete_document)

### F4 - Review MCP Server ✅
- [x] `src/mcp_servers/review/` — 3 工具 (generate_report, review_report, auto_revise)

---

## Phase G: 可视化仪表盘 ✅

基于 `st.navigation` 原生多页架构，6 个页面完全隔离，无 DOM 残留。

### G1 - 系统总览 ✅
- [x] KPI 卡片 (31省/5类/边界省份)
- [x] 综合得分排名棒棒糖图 (Top 10)
- [x] 五类布局旭日图
- [x] 布局详情表 + 气泡网格图
- [x] 边界省份警告

### G2 - 省份诊断 ✅
- [x] 省份选择器
- [x] 指标卡片 (综合得分/排名/布局/LPA/稳定性/DC枢纽)
- [x] 七维雷达图（动态范围，最大值接触外圈）
- [x] 历年趋势面积图
- [x] LISA 提示 + 边界省份警告

### G3 - 多省对比 ✅
- [x] 多选省份（最多 5 个）
- [x] 年份选择器
- [x] 对比数据表
- [x] 七维雷达叠加（颜色+线型双编码）
- [x] 历年趋势叠加

### G4 - 空间分析 ✅
- [x] Global Moran 趋势图（含显著性标注）
- [x] 中国省级 Choropleth 地图
- [x] LISA 数据表 + 类型说明
- [x] 方法说明 expander

### G5 - 布局决策 ✅
- [x] V2A 五类布局彩色卡片
- [x] 分类详情（省份列表 + 指标表）
- [x] 边界省份列表 + 保持率
- [x] V2A 规则说明 expander

### G6 - 智能问答 ✅
- [x] 数据查询 / 企划书咨询双模式切换
- [x] PDF 上传 → 自动摄入 ChromaDB
- [x] 已上传文档管理（查看/删除）
- [x] 对话历史 + 证据引用展示
- [x] ChatEngine 缓存复用

### 设计系统
- [x] 侧边栏深色渐变 + 毛玻璃导航
- [x] Metric 卡片圆角阴影
- [x] Amber 主按钮 (#D97706)
- [x] Fira Code 等宽数字 + Inter 正文
- [x] Inter 字体

---

## Phase H: 评估体系与 E2E ✅

### H1 - Golden Set 一致性测试 ✅
- [x] 31 省 × 17 字段自动校验
- [x] `src/evaluation/golden_test.py` — GoldenSetValidator

### H2 - 问答质量评估 ✅
- [x] 10 道标准问题的 QA 质量评估
- [x] 数值准确率 / 术语合规 / 证据可追溯率
- [x] `src/evaluation/qa_quality.py` — QAQualityEvaluator

### H3 - 性能测试 ✅
- [x] 问答响应时间基准
- [x] `src/evaluation/runner.py` — run_all()

---

## Phase I: 企划书评审 ✅

### I1 - 报告生成 ✅
- [x] `src/review/report_generator.py` — PDF 报告生成（fpdf2）
- [x] 企划书摘要 + 总体评估 + 逐维分析 + 替代建议 + 风险提示

### I2 - MiniMax 评审 ✅
- [x] `src/review/minimax_reviewer.py` — 5 维评分
- [x] 循环修改至 ≥ 8 分
- [x] MiniMax-M3 模型评审

---

## 五、核心设计原则

1. **数值零幻觉**: 所有数字来自数据库，LLM 只做翻译和推理。系统提示词 + _extract_evidence 双重保障。
2. **全链路可追溯**: 每个回答附带来源标注。
3. **可插拔**: LLM / Embedding / Reranker / Search 四大 Provider 通过配置切换，新增只需三步。
4. **Golden Set 驱动**: 所有输出以 01_Golden_Set.xlsx 为唯一标准答案。
5. **OpenAI SDK 统一**: 所有 LLM/Embedding 调用走 `openai.OpenAI()`。
6. **口径统一**: V2A 布局 / 修正 LISA / SHAP 代理模型 / LPA 潜在类别识别。

## 六、关键约束速查

| 场景 | 约束 |
|------|------|
| 数值回答 | 必须从数据库读取，严禁编造 |
| 城市级排名 | 拒绝回答，引导至省级 |
| 趋势判断 | "基于历史趋势"，不做精确数值预测 |
| LISA | "探索性证据"，注明 FDR 校正后无显著省份 |
| SHAP | "代理模型解释"，不称因果 |
| LPA | "潜在类别识别"，不称客观真实类型 |
| 枢纽节点 | "政策一致性"，非独立外部验证 |

## 七、项目文件清单

```
green-computing-competition/
├── main.py                          # 主入口 (8 种子命令)
├── pyproject.toml                   # 项目配置 + 依赖
├── README.md                        # 项目说明
├── DEV_SPEC.md                      # 本文档
├── .gitignore
├── .streamlit/
│   └── config.toml                  # Streamlit 主题 + 服务器配置
│
├── config/
│   ├── settings.yaml                # 全局配置 (不入库)
│   └── settings.yaml.example        # 配置模板
│
├── src/
│   ├── core/                        # 核心 (types/settings/exceptions)
│   ├── data/                        # 数据层 (database/models/loader/queries)
│   ├── libs/                        # 可插拔 Provider 层
│   │   ├── llm/                     #   DeepSeek / OpenAI
│   │   ├── embedding/               #   Qwen
│   │   ├── reranker/                #   LLM / Noop
│   │   └── search/                  #   Builtin / Noop
│   ├── ingestion/                   # PDF 摄入管线
│   │   ├── pdf_parser.py
│   │   ├── chunker.py
│   │   ├── vector_store.py          #   ChromaDB 封装
│   │   └── pipeline.py
│   ├── retrieval/
│   │   └── hybrid_search.py         #   DB + Vector → RRF → Rerank
│   ├── chat/                        # 智能问答引擎
│   │   ├── engine.py                #   分类 → 检索 → 生成 → 验证
│   │   └── prompts.py               #   系统提示词 (双模式)
│   ├── review/                      # 企划书评审
│   │   ├── report_generator.py
│   │   └── minimax_reviewer.py
│   ├── evaluation/                  # 系统评估
│   │   ├── runner.py
│   │   ├── golden_test.py
│   │   └── qa_quality.py
│   ├── mcp_servers/                 # 4 个 MCP Server
│   │   ├── data_query/              #   8 工具
│   │   ├── search/                  #   3 工具
│   │   ├── ingestion/               #   3 工具
│   │   └── review/                  #   3 工具
│   └── dashboard/                   # Streamlit 仪表盘
│       ├── app.py                   #   入口 (st.navigation)
│       ├── styles.py                #   全局 CSS
│       ├── data_loader.py           #   缓存数据加载
│       ├── components/
│       │   └── charts.py            #   Plotly 图表 (9 种)
│       └── pages/
│           ├── overview.py          #   系统总览
│           ├── province.py          #   省份诊断
│           ├── comparison.py        #   多省对比
│           ├── spatial.py           #   空间分析
│           ├── layout_page.py       #   布局决策
│           └── chat_page.py         #   智能问答
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
