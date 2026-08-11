# DEV_SPEC — 绿色算力智能决策助手 开发规格文档

> 版本: v0.3.0 | 更新: 2026-08-09 | 数据基准: NAT_FINAL

---

## 一、项目目标

将"绿色算力论文+Excel数据"升级为**可交互的智能决策支持系统**，实现:

1. **数据可视化**: 根据客户需求动态生成图表 (省份诊断、对比、空间、趋势)
2. **智能问答**: 用户提问→数据库查询→LLM生成(严禁编造数字)
3. **企划书咨询**: 企业/政府上传PDF→系统结合已有数据+联网搜索回答
4. **MCP 工具暴露**: 标准化接口供 AI 客户端调用

## 二、技术选型

| 层面 | 选型 | 说明 |
|------|------|------|
| LLM 调用 | **OpenAI SDK** (`openai>=1.0`) | 统一接口，DeepSeek/Qwen/OpenAI 均通过 `openai.OpenAI()` 调用 |
| 数据库 | **PostgreSQL** + SQLAlchemy | 与旧系统一致，连接池、pool_pre_ping |
| 向量存储 | ChromaDB | 轻量级，与 MODULAR 项目一致 |
| 可视化 | Streamlit + Plotly | 快速 Dashboard，莫兰迪配色 |
| 配置 | YAML + `${ENV:default}` | 环境变量替换，API Key 不入库 |
| MCP | mcp>=1.0 | stdio transport |

## 三、系统架构

```
┌──────────────────────────────────────────────────┐
│               MCP Client (Claude Desktop / Copilot) │
├──────────────────────────────────────────────────┤
│  mcp-data      │  mcp-search    │  mcp-ingest     │
│  数据查询(8工具) │  混合检索(3工具) │  PDF摄入(3工具)  │
├──────────────────────────────────────────────────┤
│              HybridSearcher                       │
│  DB(PostgreSQL) + Vector(ChromaDB) + Web          │
│              RRF Fusion → Rerank                   │
├──────────────────────────────────────────────────┤
│  Data Layer       │  Ingestion    │  RAG Libs     │
│  QueryEngine(SQL) │  PDF→Chunk→DB │  LLM/Emb/Rerank│
└──────────────────────────────────────────────────┘
```

### 三个 MCP Server

| Server | 启动命令 | 工具 | 功能 |
|--------|---------|------|------|
| `mcp-data` | `python main.py mcp-data` | 8 | 精确查询（省份/排名/趋势/布局/维度） |
| `mcp-search` | `python main.py mcp-search` | 3 | 混合检索（DB+Vector+Web, RRF融合） |
| `mcp-ingest` | `python main.py mcp-ingest` | 3 | PDF摄入（解析→分块→向量化→入库） |

## 四、开发阶段总览 (8 个 Phase)

| 阶段 | 内容 | 优先级 | 状态 |
|------|------|--------|------|
| **A** | 工程骨架与数据层 | ⭐⭐⭐ | ✅ 完成 |
| **B** | 可插拔 RAG Provider 层 | ⭐⭐⭐ | ✅ 完成 |
| **C** | PDF 企划书摄入管线 | ⭐⭐ | ✅ 完成 |
| **D** | 混合检索引擎 | ⭐⭐⭐ | ✅ 完成 |
| **E** | 智能问答引擎 | ⭐⭐⭐ | 🔲 下一步 |
| **F** | MCP Server (三个) | ⭐⭐ | ✅ 提前完成 |
| **G** | 可视化仪表盘 | ⭐⭐ | 🔲 待开发 |
| **H** | 评估体系与 E2E | ⭐⭐ | ✅ 完成 |

---

## Phase A: 工程骨架与数据层 ✅

### A1 - 项目结构初始化 ✅
- [x] 目录结构
- [x] pyproject.toml (含 openai, psycopg2-binary, sqlalchemy, streamlit...)
- [x] config/settings.yaml (PostgreSQL 连接, LLM/Embedding/Rerank 配置)
- [x] main.py (setup / chat / web / mcp 四种运行模式)

### A2 - 核心类型与配置 ✅
- [x] `src/core/types.py` — 7 个 dataclass + 6 个 Enum (LayoutCategory/LPAType/StabilityLabel/LISAType/...)
- [x] `src/core/settings.py` — YAML 加载 + `${ENV:default}` 环境变量替换
- [x] `src/core/exceptions.py` — 分层异常体系 (ProvinceNotFoundError, NumericHallucinationRisk...)

### A3 - 数据层 ✅
- [x] `src/data/database.py` — DatabaseManager (SQLAlchemy + PostgreSQL, 连接池)
- [x] `src/data/models.py` — 6 张 ORM 表 (province_golden, province_score_yearly, province_dimension_score, indicator_dict, lpa_province_type, indicator_raw_data)
- [x] `src/data/loader.py` — DataLoader (Excel→PostgreSQL + Golden Set 一致性验证)
- [x] `src/data/queries.py` — QueryEngine (20+ 查询方法: get_province_summary, get_top_n, get_dimension_scores, get_boundary_provinces...)

### A4 - 业务模块骨架 ✅
- [x] `src/chat/prompts.py` — 完整系统提示词 (含数值约束、LISA/SHAP/LPA 表述规范)
- [x] `src/mcp/tools.py` — 8 个 MCP 工具定义 (query_province_score, compare_provinces...)
- [x] `src/ingestion/`, `src/retrieval/`, `src/chat/`, `src/mcp/`, `src/dashboard/`, `src/evaluation/` — 包骨架

### A5 - 测试配置 ✅
- [x] `tests/conftest.py` — pytest fixtures
- [x] `README.md` — 项目说明
- [x] `DEV_SPEC.md` — 本文档

---

## Phase B: 可插拔 RAG Provider 层 ✅

### 架构模式

每层 Provider 遵循 **Base → Implementation → Factory** 三件套：

```
src/libs/
├── llm/            # ① LLM 层
│   ├── base_llm.py          # BaseLLM / Message / ChatResponse / StreamChunk
│   ├── deepseek_llm.py      # DeepSeekLLM (openai.OpenAI)
│   ├── openai_llm.py        # OpenAILLM  (openai.OpenAI)
│   └── llm_factory.py       # LLMFactory (注册表 + create + list_providers)
├── embedding/      # ② Embedding 层
│   ├── base_embedding.py    # BaseEmbedding
│   ├── qwen_embedding.py    # QwenEmbedding (openai.OpenAI, 自动分批≤10)
│   └── embedding_factory.py # EmbeddingFactory
├── reranker/       # ③ Reranker 层
│   ├── base_reranker.py     # BaseReranker / RankedDocument
│   ├── llm_reranker.py      # LLMReranker (LLM 打分 0-1)
│   └── reranker_factory.py  # RerankerFactory (含 none=NoopReranker)
└── search/         # ④ Web Search 层
    ├── base_web_search.py   # BaseWebSearch / WebSearchResult
    ├── builtin_web_search.py # BuiltinWebSearch (Phase D 对接 WebSearch 工具)
    └── web_search_factory.py # WebSearchFactory (含 none=NoopSearch)
```

### 调用链路

```
settings.yaml
    │
    ├── llm.provider: "deepseek"   → openai.OpenAI(base_url="https://api.deepseek.com")
    ├── llm.provider: "openai"     → openai.OpenAI(base_url="https://api.openai.com/v1")
    ├── embedding.provider: "qwen" → openai.OpenAI(base_url="https://dashscope.aliyuncs.com/...")
    ├── rerank.provider: "llm"     → LLMReranker(llm_provider)
    └── web_search.provider: "builtin" → BuiltinWebSearch
```

### B1 - DeepSeek LLM Provider ✅
- [x] `chat()` — 非流式对话 (openai.OpenAI)
- [x] `chat_stream()` — SSE 流式输出 (逐块 yield StreamChunk)
- [x] API Key 三级读取 (显式传参 > settings.yaml > DEEPSEEK_API_KEY)
- [x] OpenAI SDK 自动重试 + 错误处理
- [x] Token 计数 (usage.prompt_tokens / completion_tokens / total_tokens)

### B2 - OpenAI LLM Provider ✅
- [x] `chat()` + `chat_stream()` — 同上，默认端点 api.openai.com/v1
- [x] 兼容 Azure / Ollama / vLLM 等兼容端点 (改 base_url 即可)

### B3 - Qwen Embedding Provider ✅
- [x] `embed()` — 批量向量化 (openai.OpenAI, 超 10 条自动分批)
- [x] `embed_query()` — 单条查询向量化
- [x] `dimensions` — 1024 (text-embedding-v3)

### B4 - LLM Reranker ✅
- [x] `rerank()` — LLM 打分重排 (0-1 分数)
- [x] `none` 模式 — NoopReranker (不过滤)

### B5 - Web Search Provider ✅
- [x] BuiltinWebSearch 骨架 (Phase D 对接实际搜索工具)
- [x] 可信域名过滤 (miit.gov.cn, ndrc.gov.cn, stats.gov.cn...)
- [x] `none` 模式 — NoopSearch (不搜索)

### B6 - StreamChunk 流式支持 ✅
- [x] BaseLLM 提供 `chat_stream()` 默认 fallback (调用 chat 后包装为单 chunk)
- [x] DeepSeekLLM / OpenAILLM 覆盖为真正的 SSE 流式

### 新增 Provider 三步
1. 继承 Base 类 → 实现 `chat()` / `embed()` / `rerank()` / `search()`
2. 在对应 Factory 的 `_register_providers()` 中加一行注册
3. `settings.yaml` 切换 `provider: "xxx"`

### 当前注册状态

| 层 | 已注册 | 切换方式 |
|---|---|---|
| LLM | `deepseek`, `openai` | `llm.provider` |
| Embedding | `qwen` | `embedding.provider` |
| Reranker | `llm`, `none` | `retrieval.rerank.provider` |
| Web Search | `builtin`, `none` | `web_search.provider` |

---

## Phase C: PDF 企划书摄入管线 ✅

### C1 - PDF 解析 ✅
- [x] `src/ingestion/pdf_parser.py` — pdfplumber 文本 + 表格提取
- [x] `ParsedDocument` / `ParsedPage` 数据结构

### C2 - 文档分块 ✅
- [x] `src/ingestion/chunker.py` — langchain RecursiveCharacterTextSplitter
- [x] 中文语义边界优化（。；，换行符）

### C3 - 向量化与入库 ✅
- [x] `src/ingestion/vector_store.py` — ChromaDB 封装（add/search/delete/list）
- [x] `src/ingestion/pipeline.py` — 编排 PDF→Chunk→Embed→ChromaDB
- [x] Metadata 标注（来源文件、页码）

### C4 - MCP Server 封装 ✅
- [x] `src/mcp_servers/ingestion/` — 3 个工具 (ingest_document, list_documents, delete_document)

---

## Phase D: 混合检索引擎 ✅

### D1 - 关键词→SQL 映射 ✅
- [x] `src/retrieval/hybrid_search.py` — HybridSearcher
- [x] 10 种查询模式自动识别（得分/排名/趋势/维度/布局/LPA/LISA/边界/数据中心/枢纽）
- [x] 省份名 + 年份正则自动提取

### D2 - 向量检索 ✅
- [x] ChromaDB 通道已预留（需 embedding provider，Phase E 集成时接入）

### D3 - 联网搜索 ✅
- [x] BuiltinWebSearch 通道集成

### D4 - RRF 融合 ✅
- [x] 三通道去重 + 分数排序
- [x] LLMReranker 精排（可选）

### D5 - MCP Server 封装 ✅
- [x] `src/mcp_servers/search/` — 3 个工具 (search, search_db, search_web)

---

## Phase E: 智能问答引擎 🔲

### E1 - 问题分类器
- [ ] 7 种问题类型: 查询/比较/趋势/分类/解释/越界/闲聊
- [ ] 越界检测 (城市级、企业级、未来预测)

### E2 - Prompt 构建
- [ ] 检索结果→对话 Prompt (RAG_PROMPT_TEMPLATE)
- [ ] 数值约束注入 (每轮都注入 SYSTEM_PROMPT)

### E3 - 回答生成与验证
- [ ] LLM 生成 (DeepSeekLLM / OpenAILLM)
- [ ] 数值来源追溯 (每个数字→数据库字段)
- [ ] 幻觉检测 (数字是否在检索结果中出现)

### E4 - CLI 交互
- [ ] 交互式问答循环
- [ ] 历史对话管理 (max_turns=10)
- [ ] quit/help 命令

---

## Phase F: MCP Server 实现 ✅（提前完成）

### F1 - Data Query MCP Server ✅
- [x] `src/mcp_servers/data_query/` — 8 个工具
- [x] MCP SDK v2.0 API (on_list_tools / on_call_tool)
- [x] stdio transport

### F2 - Search MCP Server ✅
- [x] `src/mcp_servers/search/` — 3 个工具 (search, search_db, search_web)

### F3 - Ingestion MCP Server ✅
- [x] `src/mcp_servers/ingestion/` — 3 个工具 (ingest_document, list_documents, delete_document)

---

## Phase G: 可视化仪表盘 🔲

### G1 - 系统总览页
- [ ] KPI 卡片 (31省/5类/34指标)
- [ ] 综合得分排名柱状图
- [ ] 五类布局饼图
- [ ] 数据版本标识 (NAT_FINAL)

### G2 - 省份诊断页
- [ ] 省份选择器
- [ ] 综合得分卡片 + 七维雷达图
- [ ] 历年趋势折线图
- [ ] LPA类型 + 稳定性标签
- [ ] 障碍诊断

### G3 - 多省对比页
- [ ] 多选省份
- [ ] 综合得分对比
- [ ] 七维雷达图叠加

### G4 - 空间分析页
- [ ] 中国地图着色 (综合得分/LISA/布局)
- [ ] Global Moran 趋势图
- [ ] LISA 显著省份标注 + "探索性LISA"标签

### G5 - 布局决策页
- [ ] 布局类型分布地图
- [ ] 需求-能源二维散点图
- [ ] 边界型省份高亮

### G6 - 智能问答页
- [ ] 对话界面 + 流式输出
- [ ] 证据引用展示
- [ ] 建议问题快捷按钮

---

## Phase H: 评估体系与 E2E 🔲

### H1 - Golden Set 一致性测试
- [ ] 31 省 × 17 字段 = 527 个断言
- [ ] 自动化差分检测

### H2 - 问答质量评估
- [ ] 数值准确率 (目标 100%)
- [ ] 越界问题拒绝率 (目标 100%)
- [ ] 证据可追溯率 (目标 100%)

### H3 - 性能测试
- [ ] 问答响应时间 < 3s (含检索)
- [ ] Dashboard 页面加载 < 2s

---

## 五、核心设计原则

1. **数值零幻觉**: 所有具体数字来自数据库，LLM 只管"翻译"。系统提示词 + 后验证双重保障。
2. **全链路可追溯**: 每个回答附带 `(年份: 2024, 版本: NAT_FINAL, 来源: province_golden.composite_score)`。
3. **可插拔**: LLM / Embedding / Reranker / Search 四大 Provider 通过配置切换，新增只需三步。
4. **Golden Set 驱动**: 所有输出必须与 `01_系统标准答案_Golden_Set.xlsx` 一致。
5. **OpenAI SDK 统一**: 所有 LLM/Embedding 调用走 `openai.OpenAI()`，享受自动重试、流式、错误处理。
6. **口径统一**: 7 维度、34 指标、V2A 布局、修正 LISA。不出现旧口径。

## 六、数据依赖关系

```
05_综合评价核心结果_NAT_FINAL.xlsx (15 sheets)  ← 最完整
    ├── 版本说明
    ├── 指标字典 (34项)
    ├── 清洗数据 (279条 × 34指标)
    ├── 标准化数据 (279条)
    ├── 组合权重 (34项)
    ├── 综合得分 (279条, 2016-2024)
    ├── 七维得分 (279条)
    ├── LPA拟合 + 省份归属
    ├── Global Moran (9999次置换)
    ├── LISA 2024 (9999次条件置换)
    ├── 障碍诊断 (2024)
    ├── SHAP 代理模型检验 + 重要性
    └── 布局结果 (v2)

01_Golden_Set.xlsx ← 系统唯一标准答案 (31省 × 17字段)
02_LPA稳定性.xlsx ← LPA 验证 (n_init / Bootstrap / 留一省)
03_GlobalMoran与LISA.xlsx ← 空间统计验证 (方法修复)
04_布局规则敏感性.xlsx ← 布局规则验证 (5000 MC)
05_V2A布局与外部有效性.xlsx ← 外部验证 (50家绿色数据中心)
```

## 七、关键约束速查

| 场景 | 约束 |
|------|------|
| 数值回答 | 必须从数据库读取，严禁编造 |
| 城市/企业级排名 | 拒绝回答，引导至省级 |
| 未来预测 | 改为"历史趋势/潜力研判" |
| LISA | "探索性证据"，注明 FDR 校正后无显著省份 |
| SHAP | "代理模型解释"，不称因果 |
| LPA | "潜在类别识别"，不称客观真实类型 |
| 枢纽验证 | "政策一致性"，非独立外部验证 (X34 已入指标) |

## 八、项目文件清单

```
green-computing-competition/
├── main.py                          # 主入口 (setup/chat/web/mcp-data/mcp-search/mcp-ingest)
├── pyproject.toml
├── README.md / DEV_SPEC.md
├── config/settings.yaml             # PG + LLM + Embedding + Rerank + Web Search
├── docx/                            # NAT_FINAL Excel 数据 (已有)
├── scripts/
│   └── import_all.py                # Excel → PostgreSQL 全量导入
├── src/
│   ├── core/                        # 核心 (types/settings/exceptions)
│   ├── data/                        # 数据层
│   │   ├── database.py              #   PostgreSQL 连接管理
│   │   ├── models.py                #   ORM 模型 (映射到导入表)
│   │   ├── loader.py                #   Excel→DB 导入器
│   │   └── queries.py               #   纯 SQL 查询引擎
│   ├── libs/                        # 可插拔 RAG 层
│   │   ├── llm/                     #   BaseLLM / DeepSeekLLM / OpenAILLM / Factory
│   │   ├── embedding/               #   BaseEmbedding / QwenEmbedding / Factory
│   │   ├── reranker/                #   BaseReranker / LLMReranker / Factory
│   │   └── search/                  #   BaseWebSearch / BuiltinWebSearch / Factory
│   ├── ingestion/                   # Phase C: PDF 摄入管线
│   │   ├── pdf_parser.py            #   pdfplumber 文本+表格提取
│   │   ├── chunker.py               #   langchain 中文分块
│   │   ├── vector_store.py          #   ChromaDB 封装
│   │   └── pipeline.py              #   编排: PDF→Chunk→Embed→ChromaDB
│   ├── retrieval/                   # Phase D: 混合检索
│   │   └── hybrid_search.py         #   DB+Vector+Web → RRF → Rerank
│   ├── mcp_servers/                 # Phase F: 三个 MCP Server
│   │   ├── data_query/              #   8 工具 (省份查询/排名/趋势/布局/维度...)
│   │   ├── search/                  #   3 工具 (search/search_db/search_web)
│   │   └── ingestion/               #   3 工具 (ingest/list/delete)
│   ├── chat/                        # Phase E: 智能问答 (待做)
│   ├── dashboard/                   # Phase G: 可视化 (待做)
│   └── evaluation/                  # Phase H: 评估 (待做)
├── tests/conftest.py
├── data/db/                         # ChromaDB 向量数据
└── logs/
```
