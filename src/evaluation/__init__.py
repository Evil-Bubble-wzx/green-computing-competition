"""
评估体系 — 五维系统评估

H1: Golden Set 数据一致性 (31省核心字段 + LPA交叉验证)
H2: 问答质量评估 (关键词覆盖 + 术语合规)
H3: RAG 数字追溯 (整数+浮点数 DB 追溯 + 流式路径覆盖)
H4: 标准答案准确性 (LLM 输出 vs Golden Set)
H5: Dashboard-DB 一致性 (页面数据 vs 查询结果)
"""

from src.evaluation.golden_test import GoldenSetValidator, GoldenTestResult
from src.evaluation.lpa_validator import LPAValidator, LPAValidationResult
from src.evaluation.qa_quality import QAQualityEvaluator, QAResult, QASuiteResult
from src.evaluation.rag_traceability import RAGTraceabilityEvaluator, RAGTraceabilitySuite
from src.evaluation.qa_standard import QAStandardEvaluator, StandardAnswerSuite
from src.evaluation.dashboard_consistency import DashboardConsistencyChecker, DashboardConsistencySuite
from src.evaluation.report import ReportGenerator, EvaluationReport
from src.evaluation.runner import run_all
