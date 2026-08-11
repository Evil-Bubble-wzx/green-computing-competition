---
name: system-validator
description: Validates entire green computing system integrity. Checks PostgreSQL connection + data counts, Golden Set consistency, all modules import, API keys configured, prompts compile, MCP tools registered, Dashboard pages load. Use when user says "validate system", "check system", "系统检查", "验证系统", or before any demo/competition presentation.
---

# System Validator — 系统完整性检查

One trigger runs a full system health check. Reports pass/fail for every component. Use before demos, presentations, or after major changes.

## Pipeline

```
DB → Data Integrity → Module Import → API Keys → Prompts → MCP Tools → Dashboard
```

Run everything autonomously. Report failures clearly with fix suggestions.

## Checks

### 1. Database Connection

- Connect to PostgreSQL using `config/settings.yaml`
- Verify connection succeeds
- Check core tables exist and have expected row counts:
  - Golden Set: 31 rows
  - 综合得分: 279 rows (31省 × 9年)
  - 七维得分: 279 rows
  - 指标字典: 34 rows
  - LPA省份归属: 31 rows
  - Global Moran: 9 rows
- Log actual counts vs expected

### 2. Data Integrity

- Compare 5 random provinces from DB against `docx/01_系统标准答案_Golden_Set.xlsx`
- Verify fields match: 综合得分, 综合得分排名, 布局类型
- Check no NULL values in critical columns: 省份, 综合得分, 最终布局类型
- Confirm data version is NAT_FINAL

### 3. Module Import

- Import ALL core modules without error:
  - `src.core.{settings, types, exceptions}`
  - `src.data.{database, models, loader, queries}`
  - `src.libs.llm.{base_llm, deepseek_llm, openai_llm, llm_factory}`
  - `src.libs.embedding.{base_embedding, qwen_embedding, embedding_factory}`
  - `src.libs.reranker.{base_reranker, llm_reranker, reranker_factory}`
  - `src.libs.search.{base_web_search, builtin_web_search, web_search_factory}`
  - `src.ingestion.{pdf_parser, chunker, vector_store, pipeline}`
  - `src.retrieval.hybrid_search`
  - `src.chat.{engine, prompts}`
  - `src.review.{report_generator, minimax_reviewer}`
  - `src.evaluation.{runner, golden_test, qa_quality}`
  - `src.dashboard.{app, styles, data_loader}` + `components.charts`
  - All 4 `src/mcp_servers/*/{server,protocol_handler}` + tools
- Count total modules imported

### 4. API Keys

- Check DeepSeek API key is configured (not empty, not placeholder)
- Check Qwen Embedding API key is configured
- Check MiniMax API key is configured (optional for basic operation)
- Do NOT make real API calls — just verify keys exist in settings
- Verify keys come from env vars or settings.yaml (not hardcoded in code)

### 5. Prompts Compile

- Load `src/chat/prompts.py` without import error
- Verify `DATA_QUERY_SYSTEM_PROMPT` is non-empty and contains ALL mandatory terms:
  - "NAT_FINAL", "不得编造", "严禁自行推断"
  - "探索性局部空间证据" + "FDR" (LISA)
  - "代理模型一致性检验" (SHAP)
  - "政策一致性" (Hub)
  - "基于多期得分轨迹的潜在类别识别" (LPA)
- Verify `PROPOSAL_CONSULT_SYSTEM_PROMPT` is non-empty
- Verify `RAG_PROMPT_TEMPLATE` formats correctly with mock data

### 6. MCP Server Tools

- Load tool registrations for all 4 servers
- Verify tool counts:
  - data_query: exactly 8 tools
  - search: exactly 3 tools
  - review: exactly 3 tools
  - ingestion: exactly 3 tools
- Each tool must have: name, description, input_schema (JSON Schema dict)
- Total: 17 tools

### 7. Dashboard

- Verify all 6 page files exist and import cleanly:
  - `pages/overview.py`, `province.py`, `comparison.py`
  - `pages/spatial.py`, `layout_page.py`, `chat_page.py`
- Verify `app.py` lists 6 pages in `st.navigation`
- Verify `charts.py` has all 9 chart functions
- Verify `.streamlit/config.toml` exists

## Output Format

```
═══════════════════════════════════════════
  绿色算力系统完整性检查报告
  时间: 2026-08-11 XX:XX
═══════════════════════════════════════════

[✓] 1. PostgreSQL            localhost:5432/green_computing
                              Golden Set: 31/31 ✓  综合得分: 279/279 ✓
                              LPA: 31/31 ✓  Global Moran: 9/9 ✓

[✓] 2. 数据完整性            Golden Set 31省校验通过
                              5省抽样: 综合得分/排名/布局全部一致 ✓

[✓] 3. 模块导入              32/32 modules OK

[✓] 4. API Keys              DeepSeek ✓  Qwen ✓  MiniMax ✓

[✓] 5. Prompts               DATA_QUERY(6/6 mandatory terms) ✓
                              PROPOSAL_CONSULT ✓  RAG_TEMPLATE ✓

[✓] 6. MCP Tools             data(8) search(3) review(3) ingest(3)
                              17/17 tools registered ✓

[✓] 7. Dashboard             6/6 pages ✓  9/9 charts ✓  config ✓

═══════════════════════════════════════════
  结论: 系统健康 ✅  7/7 检查通过
═══════════════════════════════════════════
```

If any check fails, report immediately:
- Which check failed, exact error message, suggested fix

## Pre-Demo Quick Checklist

```
[ ] PostgreSQL running and accessible
[ ] Streamlit dashboard loads at localhost:8501
[ ] All 6 dashboard pages render without error
[ ] Chat page responds to data query questions
[ ] Chat page can upload and ingest PDF (if demo shows proposal consulting)
[ ] MCP servers start without errors
[ ] No ERROR in Streamlit console output
```

## Constraints

- NEVER make real LLM API calls during validation
- NEVER modify database during validation
- Conda env: `demo5`
- Work from: `/Users/evilbubble/demo5/green-computing-competition`
