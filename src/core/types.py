"""
绿色算力智能决策助手 - 核心数据类型定义

所有数据模型都在这里定义，确保类型一致性和可追溯性。
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


# =============================================================================
# 枚举类型
# =============================================================================

class LayoutCategory(str, Enum):
    """五类布局 (V2A 口径)"""
    HIGH_SUITABILITY = "高适宜综合承载区"       # 综合适宜度排名 ≤ 5
    DEMAND_DRIVEN = "需求网络驱动区"            # 需求网络优势主导
    ENERGY_LOWCARBON = "能源低碳优势承接区"     # 能源低碳禀赋主导
    POTENTIAL_PROMOTION = "综合潜力提升区"      # 剩余类，具备提升潜力
    CONSTRAINT_CONTROL = "约束控制区"           # 综合适宜度排名 ≥ 28


class LPAType(str, Enum):
    """四类 LPA 潜在剖面类型"""
    LEADING = "高位领先型"          # 类型1: 5省
    ADVANTAGED = "优势支撑型"       # 类型2: 4省 (最敏感的类别)
    CATCHING_UP = "中位追赶型"      # 类型3: 9省
    FOUNDATIONAL = "基础培育型"     # 类型4: 13省


class StabilityLabel(str, Enum):
    """稳定性标签"""
    HIGH = "高稳定"       # Bootstrap 保持率 ≥ 80%
    MEDIUM = "中稳定"     # 60% ≤ 保持率 < 80%
    BOUNDARY = "边界型"   # 保持率 < 60%


class LISAType(str, Enum):
    """LISA 空间集聚类型"""
    HH = "高-高集聚"       # 自身高 + 邻域高
    HL = "高-低离群"       # 自身高 + 邻域低
    LH = "低-高离群"       # 自身低 + 邻域高
    LL = "低-低集聚"       # 自身低 + 邻域低
    NOT_SIGNIFICANT = "不显著"


class SignificanceLevel(str, Enum):
    """统计显著性"""
    S5 = "5%显著"
    MARGINAL10 = "10%边际显著"
    NOT_SIG = "不显著"


class DimensionName(str, Enum):
    """七大维度"""
    DEMAND = "算力需求基础"
    DIGITAL_INFRA = "数字基础设施"
    ENERGY = "能源供给能力"
    GREEN_LOWCARBON = "绿色低碳约束"
    CLIMATE_NATURE = "气候与自然条件"
    INNOVATION_TALENT = "创新与人才支撑"
    REGIONAL_SYNERGY = "区域协同能力"


# =============================================================================
# 核心数据类
# =============================================================================

@dataclass
class ProvinceScore:
    """省份综合得分"""
    province: str                           # 省份名称
    year: int                               # 年份 (2016-2024)
    composite_score: float                   # 综合得分
    rank: int                                # 全国排名 (1-31)
    # 七维得分
    dim_demand: float = 0.0
    dim_digital_infra: float = 0.0
    dim_energy: float = 0.0
    dim_green_lowcarbon: float = 0.0
    dim_climate_nature: float = 0.0
    dim_innovation_talent: float = 0.0
    dim_regional_synergy: float = 0.0


@dataclass
class ProvinceGoldenRecord:
    """
    Golden Set 单省完整记录 (31省的"标准答案")

    对应文件: 01_系统标准答案_Golden_Set.xlsx → Sheet: 31省最终GoldenSet
    """
    province: str                           # 省份
    score_rank: int                         # 全国综合得分排名
    composite_score: float                   # 综合得分
    growth: float                           # 阶段增量
    demand_idx: float                       # 需求网络优势
    energy_idx: float                       # 能源低碳优势
    constraint_idx: float                   # 约束压力
    suitability: float                      # 综合适宜度
    suit_rank: int                          # 适宜度排名
    layout_type: str                        # V2A 最终布局类型
    green_dc_count_2023: int               # 2023 国家绿色数据中心数
    is_hub: bool                            # 是否国家枢纽省份
    keep_baseline_prob: float              # Bootstrap 保持原布局概率
    stability_label: str                   # 内部稳定性标签 (高稳定/中稳定/边界型)
    lisa_type_2024: str                    # 2024 修正 LISA 类型
    top5_prob: float                        # 进入 Top5 概率
    bottom4_prob: float                     # 进入 Bottom4 概率


@dataclass
class IndicatorInfo:
    """指标定义"""
    code: str                               # 指标代码 (X1-X34)
    name: str                               # 指标名称
    dimension: str                          # 所属一级维度
    direction: str                          # 指标方向 ("正向" / "逆向")


@dataclass
class BarrierDiagnosis:
    """障碍诊断结果"""
    province: str
    year: int
    primary_dimension: str                  # 首要障碍维度
    primary_score: float                    # 首要障碍度
    secondary_dimension: str                # 次要障碍维度
    secondary_score: float                  # 次要障碍度


@dataclass
class SpatialResult:
    """空间分析结果 (单年)"""
    year: int
    moran_i: float                          # Global Moran's I
    permutation_z: float                    # 置换 Z 值
    positive_p: float                       # 正向 p 值
    two_sided_p: float                      # 双侧 p 值
    significance: str                       # 显著性
    # 各省 LISA
    lisa_by_province: dict[str, LISAType] = field(default_factory=dict)


@dataclass
class LayoutDecision:
    """布局决策结果"""
    province: str
    layout_type: str                        # V2A 布局类型
    suitability: float                      # 综合适宜度
    suit_rank: int                          # 适宜度排名
    demand_idx: float                       # 需求网络优势
    energy_idx: float                       # 能源低碳优势
    constraint_idx: float                   # 约束压力
    stability_label: str                    # 稳定性标签
    is_boundary: bool                       # 是否边界重点关注


@dataclass
class ChatEvidence:
    """问答溯源证据"""
    source_type: str                        # "database" | "knowledge_base" | "web_search"
    source_name: str                        # 具体来源 (表名/文档名/URL)
    field_or_chunk: str                     # 引用的字段或文本片段
    raw_value: str                          # 原始值
    data_version: str = "NAT_FINAL"        # 数据版本
    year: Optional[int] = None              # 数据年份


@dataclass
class ChatResponse:
    """智能问答响应"""
    answer: str                             # 回答正文
    evidence: list[ChatEvidence] = field(default_factory=list)
    disclaimer: str = ""                    # 免责声明
    rejected: bool = False                  # 是否拒绝回答
    reject_reason: str = ""                 # 拒绝原因
