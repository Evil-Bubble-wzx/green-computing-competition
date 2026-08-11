---
name: review-loop
description: DeepSeek generates report → MiniMax-M3 reviews → scores on 5 dimensions → if < 8, feeds feedback back → regenerates → loops until score ≥ 8. Core quality assurance loop for proposal reports. Use when user says "评审循环", "review loop", "auto revise", "自动修改", or after generating a report that needs scoring and improvement.
---

# Review Loop — DeepSeek → MiniMax 循环评审

DeepSeek v4 Flash generates reports. MiniMax-M3 scores them on 5 dimensions. Loops until quality threshold met (≥ 8.0).

## When to Use

- After generating a proposal analysis report that needs a quality score
- When the user says "这个报告不够好，再改改"
- As optional step in proposal-pipeline (step ④.5)
- Standalone: user provides an existing report and wants iterative improvement

## Loop Flow

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│ ③ DeepSeek  │ ←── │   Feedback   │ ←── │ ② MiniMax   │
│  Regenerate │     │  (if < 8)    │     │  Review     │
└──────┬──────┘     └──────────────┘     └──────┬──────┘
       │                                        │
       │  Report Text                           │ Score + Feedback
       ▼                                        ▼
  ┌──────────────────────────────────────────────────┐
  │              Score ≥ 8.0 AND all dims ≥ 6?       │
  │         YES → Output Final Report + Score Card   │
  │         NO  → Feed feedback → Back to ③         │
  └──────────────────────────────────────────────────┘
```

## MiniMax Scoring Protocol

Uses `MiniMax-M3` via OpenAI-compatible API (`https://api.minimax.chat/v1`).

### Review Prompt (sent to MiniMax)

```
你是一个严格的绿色算力企划书评审专家。请对以下报告评分。

## 评分维度（每项 0-10，精确到整数）

| 维度 | 标准 |
|------|------|
| 数据准确性 | 数字是否与 NAT_FINAL 检索结果一致？有无编造？有无"该数据暂未收录"的诚实声明？ |
| 分析深度 | 是否覆盖全部 6 个分析维度？分析是否有洞察而非泛泛而谈？ |
| 建议合理性 | 替代省份建议是否合理？是否给出量化依据？风险提示是否到位？ |
| 格式规范 | 结构是否完整？术语是否规范（LISA/SHAP/LPA）？排版是否专业？ |
| 可操作性 | 读者能否据此做决策？建议是否具体可执行？ |

## 输出格式 (JSON only, no markdown)

{
  "total_score": X.X,
  "scores": {"数据准确性": X, "分析深度": X, "建议合理性": X, "格式规范": X, "可操作性": X},
  "passed": true/false,
  "feedback": "整体评价（2-3句）",
  "improvement_suggestions": ["具体改进1", "具体改进2", "具体改进3"]
}

通过标准: total_score ≥ 8.0 且每项 ≥ 6。任一项 < 6 即不通过。
```

### Passing Criteria (MUST enforce)

- total_score ≥ 8.0
- EVERY dimension ≥ 6
- Any dimension < 6 → FAIL, even if total ≥ 8.0
- NEVER round up — 7.95 is NOT 8.0

### Feedback Quality Requirements

MiniMax feedback MUST be:
- **Specific**: point to exact sections needing improvement (e.g., "第二段缺少贵州的具体得分数字")
- **Actionable**: ChatEngine can directly use the suggestions
- **Constructive**: say what to add/change, not just what's wrong

## DeepSeek Regeneration

When regenerating, prepend feedback context:

```
## 上一轮 MiniMax 评审反馈（请逐一改进）

{minimax_feedback}

具体改进要求：
{improvement_suggestions as numbered list}

## 原始需求
{original_query}

请针对以上反馈逐条修改报告。数据准确性是最高优先级——不得编造任何数字。
```

ChatEngine MUST:
- Address ALL improvement suggestions explicitly
- NOT remove correct content that scored well
- PRESERVE data accuracy above all — never add fake numbers to look "more analytical"
- If a suggestion conflicts with data availability, note: "该建议需要XX数据，当前检索结果未提供"

## Max Rounds

- **Default: 5 rounds**
- After 5 rounds still < 8 → output BEST version + clear warning
- Show score progression: 7.0 → 7.5 → 8.2 ✅
- If score stalls (< 0.3 improvement for 2 consecutive rounds) → ask user whether to continue

## Output Format

### During Loop
```
[Round 1/5] 🤖 MiniMax 评审中...
            数据准确性:8  分析深度:7  建议合理性:7  格式规范:7  可操作性:6
            总分: 7.0/10  ❌ 未通过
            📋 重点改进: 补充定量对比表 + 加强风险提示

[Round 2/5] 📝 根据反馈重新生成...
[Round 2/5] 🤖 MiniMax 评审中...
            数据准确性:9  分析深度:8  建议合理性:9  格式规范:8  可操作性:8
            总分: 8.4/10  ✅ 通过！
```

### Final Output
```
═══════════════════════════════════════
  评审循环完成
═══════════════════════════════════════
  最终得分: 8.4/10 ✅
  循环轮次: 2/5
  分数走势: 7.0 → 8.4

  各维度:
    数据准确性: 9/10
    分析深度:   8/10
    建议合理性: 9/10
    格式规范:   8/10
    可操作性:   8/10

  📄 最终报告: data/reports/xxx.pdf
═══════════════════════════════════════
```

## Constraints (铁律)

- NEVER skip the review step — every report MUST be scored
- NEVER lower the threshold — ≥ 8.0 is the absolute minimum
- NEVER modify MiniMax scores — use them as-is
- MiniMax API fails → retry once. Still failing → report error, don't fabricate scores
- Regeneration must NOT invent numbers to impress the reviewer
- Conda env: `demo5`
- Work from: `/Users/evilbubble/demo5/green-computing-competition`