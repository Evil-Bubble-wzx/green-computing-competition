"""
绿色算力智能决策助手 - 自定义异常

所有业务异常集中定义，便于统一错误处理。
"""


class GreenComputingError(Exception):
    """系统基础异常"""
    pass


# =============================================================================
# 数据层异常
# =============================================================================

class DataNotFoundError(GreenComputingError):
    """查询的数据不存在"""
    pass


class ProvinceNotFoundError(DataNotFoundError):
    """省份不存在"""

    def __init__(self, province: str):
        self.province = province
        super().__init__(f"省份 '{province}' 不存在 (请使用31省标准名称)")


class YearNotAvailableError(DataNotFoundError):
    """年份数据不可用"""

    def __init__(self, year: int):
        self.year = year
        super().__init__(f"年份 {year} 的数据不可用 (可用范围: 2016-2024)")


class GoldenSetMismatchError(GreenComputingError):
    """数据与 Golden Set 不一致"""
    pass


# =============================================================================
# 摄入层异常
# =============================================================================

class IngestionError(GreenComputingError):
    """文档摄入失败"""
    pass


class UnsupportedFormatError(IngestionError):
    """不支持的文档格式"""

    def __init__(self, format: str):
        self.format = format
        super().__init__(f"不支持的文档格式: {format}")


class PDFParseError(IngestionError):
    """PDF 解析失败"""
    pass


# =============================================================================
# 检索层异常
# =============================================================================

class RetrievalError(GreenComputingError):
    """检索失败"""
    pass


class WebSearchError(RetrievalError):
    """联网搜索失败"""
    pass


# =============================================================================
# 问答层异常
# =============================================================================

class ChatError(GreenComputingError):
    """问答处理异常"""
    pass


class OutOfScopeError(ChatError):
    """问题超出系统能力范围"""

    def __init__(self, reason: str = ""):
        self.reason = reason
        msg = f"问题超出系统范围: {reason}" if reason else "问题超出系统范围"
        super().__init__(msg)


class NumericHallucinationRisk(ChatError):
    """检测到数值幻觉风险"""

    def __init__(self, field: str):
        self.field = field
        super().__init__(f"数值 '{field}' 未从数据库查询到，拒绝编造")
