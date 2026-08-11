"""
ORM 模型定义 (SQLAlchemy)

映射 NAT_FINAL 数据到关系型表结构。
"""

from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    Boolean,
    Index,
    PrimaryKeyConstraint,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


# =============================================================================
# 省份 Golden Set 主表 (系统唯一标准答案)
# =============================================================================

class ProvinceGolden(Base):
    """
    31省 Golden Set 记录

    对应: 01_系统标准答案_Golden_Set.xlsx → 31省最终GoldenSet
    这是系统唯一标准答案，所有展示和问答必须与此一致。
    """
    __tablename__ = "01_系统标准答案_Golden_Set_31省最终GoldenSet"

    province = Column(String, primary_key=True, comment="省份 (31省标准名称)")
    score_rank = Column(Integer, nullable=False, comment="全国综合得分排名 (1-31)")
    composite_score = Column(Float, nullable=False, comment="综合得分")
    growth = Column(Float, comment="阶段增量")
    demand_idx = Column(Float, comment="需求网络优势")
    energy_idx = Column(Float, comment="能源低碳优势")
    constraint_idx = Column(Float, comment="约束压力")
    suitability = Column(Float, comment="综合适宜度")
    suit_rank = Column(Integer, comment="适宜度排名")
    layout_type = Column(String, comment="最终布局类型 (V2A口径)")
    green_dc_count_2023 = Column(Integer, comment="2023国家绿色数据中心数")
    is_hub = Column(Boolean, comment="是否国家枢纽省份")
    keep_baseline_prob = Column(Float, comment="保持原布局概率")
    stability_label = Column(String, comment="内部稳定性标签")
    lisa_type_2024 = Column(String, comment="2024修正LISA类型")
    top5_prob = Column(Float, comment="进入Top5概率")
    bottom4_prob = Column(Float, comment="进入Bottom4概率")

    data_version = Column(String, default="NAT_FINAL")
    updated_at = Column(String, comment="数据更新时间")

    __table_args__ = (
        Index("idx_province_golden_layout", "layout_type"),
        Index("idx_province_golden_stability", "stability_label"),
    )


# =============================================================================
# 年度综合得分表 (2016-2024 × 31省 = 279条)
# =============================================================================

class ProvinceScoreYearly(Base):
    """
    各省逐年综合得分

    对应: 05_综合评价核心结果_NAT_FINAL.xlsx → 综合得分
    """
    __tablename__ = "province_score_yearly"

    province = Column(String, primary_key=True, comment="省份")
    year = Column(Integer, primary_key=True, comment="年份 (2016-2024)")
    composite_score = Column(Float, nullable=False, comment="综合得分")
    rank = Column(Integer, comment="当年排名")

    __table_args__ = (
        Index("idx_score_year", "year"),
        Index("idx_score_province_year", "province", "year"),
    )


# =============================================================================
# 七维得分表
# =============================================================================

class ProvinceDimensionScore(Base):
    """
    各省逐年七维得分

    对应: 05_综合评价核心结果_NAT_FINAL.xlsx → 七维得分
    """
    __tablename__ = "province_dimension_score"

    province = Column(String, primary_key=True)
    year = Column(Integer, primary_key=True)
    dim_demand = Column(Float, comment="算力需求基础")
    dim_digital_infra = Column(Float, comment="数字基础设施")
    dim_energy = Column(Float, comment="能源供给能力")
    dim_green_lowcarbon = Column(Float, comment="绿色低碳约束")
    dim_climate_nature = Column(Float, comment="气候与自然条件")
    dim_innovation_talent = Column(Float, comment="创新与人才支撑")
    dim_regional_synergy = Column(Float, comment="区域协同能力")

    __table_args__ = (
        Index("idx_dim_year", "year"),
    )


# =============================================================================
# 指标字典表 (34项)
# =============================================================================

class IndicatorDict(Base):
    """
    34项指标字典

    对应: 05_综合评价核心结果_NAT_FINAL.xlsx → 指标字典
    """
    __tablename__ = "indicator_dict"

    code = Column(String, primary_key=True, comment="指标代码 (X1-X34)")
    name = Column(String, nullable=False, comment="指标名称")
    dimension = Column(String, nullable=False, comment="一级维度")
    direction = Column(String, nullable=False, comment="指标方向 (正向/逆向)")

    __table_args__ = (
        Index("idx_ind_dimension", "dimension"),
    )


# =============================================================================
# LPA 类型归属表
# =============================================================================

class LPAProvinceType(Base):
    """
    各省 LPA 类型归属

    对应: 05_综合评价核心结果_NAT_FINAL.xlsx → LPA省份归属
    """
    __tablename__ = "lpa_province_type"

    province = Column(String, primary_key=True)
    lpa_type = Column(Integer, comment="LPA类型编号 (1-4)")
    lpa_type_name = Column(String, comment="类型命名")
    max_posterior = Column(Float, comment="最大后验概率")
    stability_label = Column(String, comment="Bootstrap 稳定性标签")
    is_boundary = Column(Boolean, default=False, comment="是否边界省份")


# =============================================================================
# 指标原始数据表 (279条 × 34指标)
# =============================================================================

class IndicatorRawData(Base):
    """
    指标原始数据 (清洗后)

    对应: 05_综合评价核心结果_NAT_FINAL.xlsx → 清洗数据
    """
    __tablename__ = "indicator_raw_data"

    province = Column(String, primary_key=True)
    year = Column(Integer, primary_key=True)
    x1 = Column(Float, comment="GDP（亿元）")
    x2 = Column(Float, comment="常住人口（万人)")
    x3 = Column(Float, comment="能源消费总量")
    x4 = Column(Float, comment="CO2排放量（吨）")
    x5 = Column(Float, comment="每万人光缆线路长度")
    x6 = Column(Float, comment="每万人5G基站数")
    x7 = Column(Float, comment="每万人接入端口数")
    x8 = Column(Float, comment="单位GDP能耗")
    x9 = Column(Float, comment="可再生能源发电占比")
    x10 = Column(Float, comment="碳排放强度（吨/万元）")
    x11 = Column(Float, comment="信息传输、软件和信息技术服务业增加值占GDP比重")
    x12 = Column(Float, comment="电信业务发展强度")
    x13 = Column(Float, comment="全员劳动生产率")
    x14 = Column(Float, comment="R&D经费投入强度")
    x15 = Column(Float, comment="万人发明专利占比")
    x16 = Column(Float, comment="高技术产业投资强度")
    x17 = Column(Float, comment="每万人发电装机容量")
    x18 = Column(Float, comment="移动电话普及率")
    x19 = Column(Float, comment="移动互联网用户普及水平")
    x20 = Column(Float, comment="每万人互联网宽带接入用户数")
    x21 = Column(Float, comment="年平均气温")
    x22 = Column(Float, comment="信息技术从业人员占比")
    x23 = Column(Float, comment="人均水资源量")
    x24 = Column(Float, comment="科学技术支出占比")
    x25 = Column(Float, comment="全社会用电量")
    x26 = Column(Float, comment="人均全社会用电量")
    x27 = Column(Float, comment="一般工业固体废物综合利用率")
    x28 = Column(Float, comment="节能环保支出强度")
    x29 = Column(Float, comment="第三产业增加值")
    x30 = Column(Float, comment="R&D人员全时当量")
    x31 = Column(Float, comment="绿色专利申请量")
    x32 = Column(Float, comment="政府科技支出")
    x33 = Column(Float, comment="数字普惠金融指数")
    x34 = Column(Integer, comment="国家算力枢纽节点编码")

    __table_args__ = (
        Index("idx_raw_year", "year"),
    )
