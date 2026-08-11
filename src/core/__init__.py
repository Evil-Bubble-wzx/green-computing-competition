"""
核心模块: 配置加载、类型定义、异常定义
"""

from src.core.settings import Settings, SettingsError, load_settings
from src.core.types import (
    ProvinceScore,
    ProvinceGoldenRecord,
    IndicatorInfo,
    BarrierDiagnosis,
    SpatialResult,
    LayoutDecision,
    ChatEvidence,
    ChatResponse,
    LayoutCategory,
    LPAType,
    StabilityLabel,
    LISAType,
    SignificanceLevel,
    DimensionName,
)
from src.core.exceptions import (
    GreenComputingError,
    DataNotFoundError,
    ProvinceNotFoundError,
    YearNotAvailableError,
    IngestionError,
    RetrievalError,
    ChatError,
    OutOfScopeError,
    NumericHallucinationRisk,
)

__all__ = [
    # Settings
    "Settings",
    "SettingsError",
    "load_settings",
    # Types
    "ProvinceScore",
    "ProvinceGoldenRecord",
    "IndicatorInfo",
    "BarrierDiagnosis",
    "SpatialResult",
    "LayoutDecision",
    "ChatEvidence",
    "ChatResponse",
    "LayoutCategory",
    "LPAType",
    "StabilityLabel",
    "LISAType",
    "SignificanceLevel",
    "DimensionName",
    # Exceptions
    "GreenComputingError",
    "DataNotFoundError",
    "ProvinceNotFoundError",
    "YearNotAvailableError",
    "IngestionError",
    "RetrievalError",
    "ChatError",
    "OutOfScopeError",
    "NumericHallucinationRisk",
]
