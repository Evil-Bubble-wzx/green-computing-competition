"""
共享测试题 + 标准答案

10 道标准测试题，供 H2(问答质量) 和 H4(标准答案准确性) 共用。
标准答案从 Golden Set 动态加载，确保与数据库同步。
"""

from __future__ import annotations

from typing import Optional


# =========================================================================
# 10 道标准测试题
# =========================================================================

TEST_QUESTIONS = [
    {
        "id": "Q1",
        "question": "江苏2024年综合得分排名第几？",
        "mode": "data_query",
        "expect_numbers": ["0.573", "1"],
        "expect_keywords": ["江苏", "排名", "2024"],
        "forbidden": ["不确定", "可能", "大约"],
    },
    {
        "id": "Q2",
        "question": "广东和浙江哪个综合得分更高？",
        "mode": "data_query",
        "expect_numbers": ["0.564", "0.562"],
        "expect_keywords": ["广东"],
        "forbidden": [],
    },
    {
        "id": "Q3",
        "question": "高适宜综合承载区有哪些省份？",
        "mode": "data_query",
        "expect_numbers": ["5"],
        "expect_keywords": ["江苏", "广东", "浙江", "北京", "上海"],
        "forbidden": [],
    },
    {
        "id": "Q4",
        "question": "北京历年综合得分趋势如何？",
        "mode": "data_query",
        "expect_numbers": ["0."],
        "expect_keywords": ["2016", "2024", "上升", "增长"],
        "forbidden": [],
    },
    {
        "id": "Q5",
        "question": "布局边界省份有哪些？",
        "mode": "data_query",
        "expect_numbers": [],
        "expect_keywords": ["四川", "边界"],
        "forbidden": [],
    },
    {
        "id": "Q6",
        "question": "杭州2025年数据中心的发展趋势预测",
        "mode": "data_query",
        "expect_numbers": [],
        "expect_keywords": [],
        "forbidden": [],
        "should_reject": True,
    },
    {
        "id": "Q7",
        "question": "LISA显著省份有哪些？",
        "mode": "data_query",
        "expect_numbers": [],
        "expect_keywords": ["上海", "江苏", "内蒙古", "广东", "福建", "探索性"],
        "forbidden": ["确定性", "显著集聚"],
    },
    {
        "id": "Q8",
        "question": "贵州属于什么布局类型？",
        "mode": "data_query",
        "expect_numbers": [],
        "expect_keywords": ["能源低碳优势承接区"],
        "forbidden": [],
    },
    {
        "id": "Q9",
        "question": "什么因素影响绿色算力得分？",
        "mode": "data_query",
        "expect_numbers": ["7"],
        "expect_keywords": ["维度", "指标", "评价"],
        "forbidden": [],
    },
    {
        "id": "Q10",
        "question": "哪些省份适合建绿色数据中心？",
        "mode": "data_query",
        "expect_numbers": [],
        "expect_keywords": ["高适宜", "能源", "布局"],
        "forbidden": [],
    },
]


# =========================================================================
# 标准答案 — 从 Golden Set 推算
# =========================================================================

# 静态部分：可预先定义的正确答案
STANDARD_ANSWERS: dict = {
    "Q1": {
        "province": "江苏",
        "field": "全国综合得分排名",
        "expected_rank": 1,
        "expected_score_range": (0.57, 0.58),
        "description": "江苏2024年综合得分排名全国第1，综合得分约0.5733",
    },
    "Q2": {
        "compare": [
            {"province": "广东", "score": 0.5643, "rank": 2},
            {"province": "浙江", "score": 0.5620, "rank": 3},
        ],
        "winner": "广东",
        "description": "广东综合得分(0.5643)高于浙江(0.5620)，广东排名第2，浙江排名第3",
    },
    "Q3": {
        "expected_provinces": ["江苏", "广东", "浙江", "北京", "上海"],
        "expected_count": 5,
        "description": "高适宜综合承载区共5省：江苏、广东、浙江、北京、上海",
    },
    "Q4": {
        "province": "北京",
        "year_range": (2016, 2024),
        "trend_keywords": ["上升", "增长", "提升", "改善"],
        "description": "北京2016-2024年综合得分呈上升趋势",
    },
    "Q5": {
        "concept": "布局边界省份（保持原布局概率较低）",
        "must_include": ["四川"],
        "description": "四川、陕西、安徽为布局边界省份，保持原布局概率较低",
    },
    "Q6": {
        "should_reject": True,
        "description": "城市级查询应被拒绝，仅支持省级评估",
    },
    "Q7": {
        "concept": "LISA空间集聚显著省份",
        "must_include": ["上海", "江苏", "内蒙古", "广东", "福建"],
        "must_not_include": ["确定性", "显著集聚"],
        "must_include_terms": ["探索性"],
        "description": "LISA分析显示上海、江苏等地呈现显著空间集聚模式（探索性证据）",
    },
    "Q8": {
        "province": "贵州",
        "expected_layout": "能源低碳优势承接区",
        "description": "贵州属于能源低碳优势承接区",
    },
    "Q9": {
        "concept": "绿色算力影响因素",
        "expected_dimension_count": 7,
        "expected_dimensions": [
            "算力需求基础", "数字基础设施", "能源供给能力", "绿色低碳约束",
            "气候与自然条件", "创新与人才支撑", "区域协同能力",
        ],
        "description": "绿色算力得分由7个维度34项指标综合评价得出",
    },
    "Q10": {
        "concept": "适合建绿色数据中心的省份",
        "must_include": ["高适宜", "能源", "布局"],
        "expected_layouts": ["高适宜综合承载区", "能源低碳优势承接区"],
        "description": "高适宜综合承载区和能源低碳优势承接区最适合建设绿色数据中心",
    },
}


def load_standard_answers(db) -> dict:
    """
    从 Golden Set 数据库动态加载标准答案，确保与数据同步。

    覆盖 Q1-Q3 的动态数值（其他 Q 的答案是结构性的，静态定义即可）。

    Args:
        db: DatabaseManager 实例

    Returns:
        dict: 合并后的标准答案（静态 + 动态）
    """
    from src.data.queries import QueryEngine, TBL_GOLDEN

    qe = QueryEngine(db)
    answers = dict(STANDARD_ANSWERS)  # 浅拷贝

    try:
        # Q1: 江苏排名 + 得分
        jiangsu = qe.get_province_summary("江苏")
        answers["Q1"] = {
            **answers["Q1"],
            "expected_rank": jiangsu.score_rank,
            "expected_score_range": (
                jiangsu.composite_score - 0.01,
                jiangsu.composite_score + 0.01,
            ),
            "description": f"江苏2024年综合得分排名全国第{jiangsu.score_rank}，综合得分约{jiangsu.composite_score:.4f}",
        }

        # Q2: 广东 vs 浙江
        guangdong = qe.get_province_summary("广东")
        zhejiang = qe.get_province_summary("浙江")
        winner = "广东" if guangdong.composite_score > zhejiang.composite_score else "浙江"
        answers["Q2"] = {
            **answers["Q2"],
            "compare": [
                {"province": "广东", "score": round(guangdong.composite_score, 4), "rank": guangdong.score_rank},
                {"province": "浙江", "score": round(zhejiang.composite_score, 4), "rank": zhejiang.score_rank},
            ],
            "winner": winner,
            "description": f"{winner}综合得分更高",
        }

        # Q3: 高适宜综合承载区省份列表
        high_suit = qe.get_provinces_by_layout("高适宜综合承载区")
        answers["Q3"] = {
            **answers["Q3"],
            "expected_provinces": high_suit,
            "expected_count": len(high_suit),
            "description": f"高适宜综合承载区共{len(high_suit)}省：{'、'.join(high_suit)}",
        }
    except Exception:
        pass  # 如果 DB 不可用，使用静态默认值

    return answers
