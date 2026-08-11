---
name: dev-guide
description: Enforces green computing project development conventions. Config-driven architecture, Factory pattern for providers, prompt discipline, Golden Set integrity, dashboard conventions, MCP server structure. Use when user says "开发规范", "dev guide", "coding rules", "帮我写代码", or before ANY coding task in this project.
---

# Dev Guide — 绿色算力项目开发规范

Activated BEFORE any coding task. Ensures all code follows project conventions. Violating any rule produces broken or unmaintainable code.

## Golden Rules (Verify Before Every Edit)

### 1. Config-Driven — No Hardcoding

- All API keys, URLs, model names → `config/settings.yaml`
- Settings loaded via `src/core/settings.py` dataclasses
- `${ENV:default}` pattern for secrets
- All prompts → `src/chat/prompts.py` as module-level constants
- NEVER hardcode credentials, paths, or model names anywhere
- New config sections → add corresponding dataclass in `settings.py`
- `config/settings.yaml` is in `.gitignore` — NEVER commit it
- Template provided: `config/settings.yaml.example`

### 2. Factory Pattern — All Providers

Every pluggable component follows: **Base → Implementation → Factory**

```
src/libs/<layer>/
├── base_<layer>.py        # Abstract base class
├── <provider>_<layer>.py  # Implementation
└── <layer>_factory.py     # Factory with registry
```

- New LLM? Inherit `BaseLLM`, register in `LLMFactory`
- New Embedding? Inherit `BaseEmbedding`, register in `EmbeddingFactory`
- New tool? Register in `src/mcp_servers/*/tools/__init__.py`
- Don't break the pattern — don't add standalone classes

### 3. Prompt Discipline

ALL prompts in `src/chat/prompts.py`:

- `DATA_QUERY_SYSTEM_PROMPT` — data queries, trends, comparisons, recommendations
- `PROPOSAL_CONSULT_SYSTEM_PROMPT` — PDF proposal analysis
- `RAG_PROMPT_TEMPLATE` — retrieval context wrapper

Every prompt MUST preserve:
- "NAT_FINAL" — data version
- "不得编造" / "严禁自行推断" — zero hallucination
- "探索性局部空间证据" (LISA) + "FDR 校正后无显著省份"
- "代理模型一致性检验" (SHAP)
- "政策一致性" (Hub)
- "基于多期得分轨迹的潜在类别识别" (LPA)

After ANY prompt edit → run data-guardian to verify no regression.

### 4. Golden Set Integrity

- Golden Set (`01_系统标准答案_Golden_Set.xlsx`) is the single source of truth
- All outputs must match Golden Set values exactly
- Adding a new query? Verify against Golden Set first
- Don't add alternative "interpretations" of the data
- Run `python main.py evaluate` after data changes

### 5. Dashboard Conventions

```
src/dashboard/
├── app.py                   # st.navigation entry, set_page_config
├── styles.py                # Global CSS injection
├── data_loader.py           # @st.cache_resource loaders
├── components/
│   └── charts.py            # Plotly chart functions (pure, no Streamlit calls)
└── pages/
    └── *.py                 # Flat scripts (module-level code, no show() wrapper)
```

- Dashboard uses `st.navigation` with file-based `st.Page` — each page is standalone
- Chart functions take data, return `go.Figure` — no `st.*` calls inside
- CSS in `styles.py` — minimal, only what Streamlit can't do natively
- `@st.cache_resource` for QueryEngine, ChatEngine, IngestionPipeline
- Sidebar: dark gradient (#0F172A → #1E3A5F), navigation radio

### 6. MCP Server Structure

Every server follows:

```
src/mcp_servers/<name>/
├── server.py             # Entry: load config → build → run stdio
├── protocol_handler.py   # create_<name>_server() factory
└── tools/__init__.py     # register_all(handler, ...deps)
```

Each tool: async function, registered with name + description + JSON Schema, returns JSON string.

### 7. Table Name Reference

Use exact Chinese table names from PostgreSQL:

```
TBL_GOLDEN    = "01_系统标准答案_Golden_Set_31省最终GoldenSet"
TBL_SCORE     = "05_综合评价核心结果_NAT_FINAL_综合得分"
TBL_DIM       = "05_综合评价核心结果_NAT_FINAL_七维得分"
TBL_INDICATOR = "05_综合评价核心结果_NAT_FINAL_指标字典"
TBL_LPA       = "05_综合评价核心结果_NAT_FINAL_LPA省份归属"
TBL_RAW       = "05_综合评价核心结果_NAT_FINAL_清洗数据"
```

Full list: `src/data/queries.py` TBL_* constants. NEVER invent table names.

### 8. Python Environment

- Conda env: `demo5` (`/opt/miniconda3/envs/demo5`)
- Python: 3.13
- Package manager: pip (within conda env)
- Project root: `/Users/evilbubble/demo5/green-computing-competition`

## Pre-Code Checklist

Before writing ANY code:
```
[ ] Config-driven?            Settings in settings.yaml + settings.py
[ ] Factory pattern?          If new provider: Base→Impl→Factory
[ ] Prompt safe?              Not violating terminology constraints
[ ] Golden Set compatible?    Outputs match Golden Set values
[ ] Table names correct?      Using TBL_* constants
[ ] Dashboard convention?     Chart=no st calls, page=flat script
[ ] MCP structure?            server.py + protocol_handler.py + tools/__init__.py
[ ] Conda env active?         Using demo5
```

## Forbidden Patterns

| ❌ Don't | ✅ Do |
|---------|------|
| Hardcode API keys | `settings.llm.api_key` |
| Write prompts inline | Add to `src/chat/prompts.py` |
| Break MCP server structure | Follow server/protocol/tools pattern |
| Use English column names in SQL | Use actual Chinese column names |
| Call Golden Set from memory | Query the database |
| Put st.* calls in chart functions | Charts return go.Figure only |
| Commit settings.yaml | It's in .gitignore |
| Use show() wrappers in dashboard pages | Flat scripts for st.Page |

## Quick Reference: Key Files

| Purpose | File |
|---------|------|
| System config | `config/settings.yaml` |
| Config dataclasses | `src/core/settings.py` |
| All prompts | `src/chat/prompts.py` |
| DB tables + SQL | `src/data/queries.py` |
| Chat engine | `src/chat/engine.py` |
| PDF pipeline | `src/ingestion/pipeline.py` |
| Hybrid search | `src/retrieval/hybrid_search.py` |
| Dashboard entry | `src/dashboard/app.py` |
| Dashboard charts | `src/dashboard/components/charts.py` |
| Dashboard styles | `src/dashboard/styles.py` |
| Report generator | `src/review/report_generator.py` |
| MiniMax reviewer | `src/review/minimax_reviewer.py` |
| Golden Set validator | `src/evaluation/golden_test.py` |
