---
name: proposal-pipeline
description: Full proposal analysis pipeline. Two paths: (1) Dashboard — upload PDF in chat page → ChatEngine analyzes with DB+Vector search. (2) CLI — python main.py chat → mode switch. Pipeline: Ingest PDF → HybridSearch (DB+Vector) → ChatEngine analysis → Optional MiniMax review loop. Use when user says "分析企划书", "analyze proposal", "完整流程", "full pipeline", or provides a PDF proposal file.
---

# Proposal Pipeline — 企划书全流程分析

Two paths to analyze a proposal: Dashboard (recommended) or CLI.

## Path A: Dashboard (推荐)

```
Dashboard 聊天页 → 切换到 📄 企划书咨询
→ 上传 PDF (自动摄入 ChromaDB)
→ 输入问题 (如"这个方案在贵州落地可行吗？")
→ ChatEngine 双通道检索 (DB + Vector)
→ 逐维分析 + 匹配度评分 + 风险提示
```

No extra config needed. ChatEngine is cached (`@st.cache_resource`).

## Path B: CLI

```bash
python main.py chat
# 输入 mode → 切换到企划书咨询模式
# 输入问题
```

## Pipeline (Internal)

```
┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐
│ ① Ingest │ → │ ② Search │ → │ ③ Analyze│ → │ ④ Output │
│  PDF→DB  │    │ DB+Vector│    │ ChatEngine│   │  Report  │
└──────────┘    └──────────┘    └──────────┘    └──────────┘
```

If MiniMax review is desired (for scored PDF report), add step ④.5:

```
→ │ ④.5 Review│ → (score < 8? feedback → back to ③)
   │ MiniMax   │
```

## Input Requirements

- **PDF file** (required) — uploaded via Dashboard or MCP ingest tool
- **Target province** (optional) — can be extracted from PDF or user question
- **Analysis question** (required) — what the user wants to know

## Step-by-Step

### ① Ingest

Dashboard:
- User uploads PDF via `st.file_uploader` in chat page
- `IngestionPipeline.ingest()`: parse → chunk → embed → ChromaDB
- Dedup: `st.session_state.ingested_files` prevents re-ingestion
- Confirm: toast "✅ xxx.pdf 已就绪"

CLI:
- Use `python main.py mcp-ingest` or call pipeline directly

### ② Search

HybridSearcher runs two channels:
1. **DB search** — keyword → SQL, matching province + topic patterns
2. **Vector search** — embed query → ChromaDB cosine search over PDF chunks

Fusion: RRF ranking, deduplication, optional LLM rerank.

### ③ Analyze

ChatEngine with `mode="proposal_consult"`:

System prompt guides the LLM to:
1. Extract key fields from PDF: IT load, PUE, green power ratio, business type, target province
2. Match against NAT_FINAL data for target province(s)
3. Analyze across 6 dimensions: demand, energy, constraints, location, policy, stability
4. Score match level (☆ 1-5)
5. Suggest 2-3 alternative provinces with quantitative evidence
6. Flag risks: LPA stability, boundary provinces, talent gaps, cost concerns

CRITICAL: Every number in the answer must come from retrieval results. Never fabricate.

### ④ Output

Dashboard: renders directly in chat with expandable evidence section.

CLI: prints to terminal.

Optional PDF report: `python main.py mcp-review` → `auto_revise` tool.

## Constraints (铁律)

- ALL numbers from NAT_FINAL or PDF — never fabricate
- PDF parse failure → tell user, don't guess
- Vector search returns empty → note "PDF content not found in retrieval"
- DB returns no province match → note "NAT_FINAL data not available for this province"
- If both channels empty → disclaimer: "分析仅基于大模型常识，非NAT_FINAL官方数据"
- ChatEngine is cached — reuse, don't recreate per message
- Conda env: `demo5`
- Work from: `/Users/evilbubble/demo5/green-computing-competition`
