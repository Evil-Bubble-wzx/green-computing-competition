---
name: data-guardian
description: Guards against data hallucination in the green computing system. Validates every answer — numbers must trace to NAT_FINAL retrieval results, terminology must comply (LISA/SHAP/LPA), evidence must be traceable. Covers data queries, trend analysis, and recommendation answers. Use when user says "数据校验", "guardian", "check accuracy", "幻觉检查", "verify answers", or when modifying prompts/retrieval/engine logic.
---

# Data Guardian — 数据守护神

Prevents hallucination. Every number in every answer MUST trace back to NAT_FINAL retrieval results. Zero tolerance for fabricated data.

## Pipeline

```
Sample Questions → Generate Answers → Validate Numbers → Check Terminology → Report
```

Run all 10 questions. Each answer gets a pass/fail on 4 dimensions.

## Rules (from DEV_SPEC §6)

### 1. Numeric Zero-Hallucination (铁律)

Every float in the answer must appear verbatim in the retrieval results.
- Extract all floats from answer (regex: `\d+\.\d{2,}`)
- Cross-reference with retrieval result content
- Flag any number NOT found in retrieval → **HALLUCINATION**
- Applies to: scores, rankings, probabilities, counts, percentages

### 2. Terminology Compliance (铁律)

| Term | ❌ Forbidden | ✅ Required |
|------|-------------|-----------|
| LISA | "显著", "确定", "证明", "集聚显著" | "探索性局部空间证据" + 注明"FDR校正后无显著省份" |
| SHAP | "因果", "预测", "解释力", "重要性排名" | "代理模型一致性检验"（XGBoost 逼近 TOPSIS） |
| LPA | "客观类型", "真实类别", "本质分类" | "基于多期得分轨迹的潜在类别识别" |
| Trend | "未来5年将", "预测会", "将会达到" | "历史趋势显示", "基于2016-2024数据", "呈XX态势" |
| Hub | "外部验证", "独立验证", "第三方验证" | "政策一致性"（X34 已进入指标体系） |

- Scan answer text for forbidden terms
- Flag ANY occurrence → **TERMINOLOGY VIOLATION**
- No "it's close enough" — exact wording matters

### 3. Evidence Traceability

- Every factual claim must cite a source
- Check answer contains: year (2016-2024), data version (NAT_FINAL), source table/field
- For recommendation answers: must cite specific province scores, layout types, LPA types
- For trend answers: must cite historical data range and stability labels
- Flag if answer lacks evidence → **EVIDENCE GAP**

### 4. Scope Boundaries

- ✅ Allowed: provincial queries, trends, comparisons, recommendations, proposal analysis
- ❌ Rejected: city-level exact rankings, enterprise-level data, precise numerical predictions (e.g. "2027得分0.6")
- Verify out-of-scope questions get properly rejected or reframed — NOT hallucinated

## Test Questions (10 Golden Questions)

| # | Question | Valid Answer Must |
|---|----------|-------------------|
| 1 | 江苏2024年综合得分排名第几？ | 排名=1, 得分=0.5733, 来源标注 |
| 2 | 广东和浙江哪个综合得分更高？ | 广东(0.5643) > 浙江(0.5620), 数字来自DB |
| 3 | 高适宜综合承载区有哪些省份？ | 5省: 江苏/广东/浙江/北京/上海 |
| 4 | 北京历年综合得分趋势如何？ | 9年数据, 2024最高, 引用具体年份 |
| 5 | 布局边界省份有哪些？ | 四川/陕西/安徽, 保持率<80%, 数字准确 |
| 6 | 杭州2025年数据中心预测？ | 应拒绝(城市级+未来预测) |
| 7 | LISA显著省份有哪些？ | HH:上海/江苏, HL:内蒙古/广东, LH:福建 + FDR说明 |
| 8 | 贵州属于什么布局类型？ | 能源低碳优势承接区, 排名20, 得分0.348384 |
| 9 | 什么因素影响绿色算力得分？ | 引用7维34指标, 不编造权重 |
| 10 | 哪些省份适合建AI训练中心？ | 推荐类回答, 每省附具体得分, 用DB数据 |

## Output Format

```
═══════════════════════════════════════
  数据守护神 — 回答质量报告
═══════════════════════════════════════

[Q1] "江苏2024年综合得分排名第几？"
  Answer: 排名第1, 得分0.5733
  Numbers: 0.5733 → found in retrieval ✓
  Terms: no violations ✓
  Evidence: year=2024, NAT_FINAL, Golden Set ✓
  Result: PASS ✅

[Q6] "杭州2025年数据中心预测？"
  Answer: 抱歉，本系统不提供城市级预测...
  Rejected correctly ✓
  Result: PASS ✅

[Q10] "哪些省份适合建AI训练中心？"
  Answer: 江苏(0.5733)... 北京(0.5426)... 贵州...
  Numbers: 5/5 found in DB ✓
  Terms: "历史趋势" used, no "未来预测" ✓
  Evidence: 每省附得分+排名 ✓
  Result: PASS ✅

═══════════════════════════════════════
  10/10 通过 ✅
  Hallucinations: 0
  Terminology Violations: 0
  Evidence Gaps: 0
═══════════════════════════════════════
```

## Constraints

- Use REAL ChatEngine with DeepSeek API — no mocking
- Compare every number against retrieval results, not memory
- Flag even minor terminology violations — zero tolerance
- If hallucination found, diagnose root cause: prompt? retrieval gap? LLM behavior?
- Recommends fix: adjust prompt / add retrieval pattern / change classifier
- After prompts.py or engine.py is modified, MUST re-run this guardian
- Python env: conda `demo5`
- Work from: `/Users/evilbubble/demo5/green-computing-competition`
