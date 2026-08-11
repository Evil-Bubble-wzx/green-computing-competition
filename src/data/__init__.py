"""
数据层: 数据库连接、ORM 模型、Excel 导入、查询封装

职责:
- 管理 SQLite 数据库连接
- 定义 Province、Indicator、Score 等模型
- 从 NAT_FINAL Excel 文件导入数据
- 提供结构化查询接口 (按省份、年份、维度等)
"""

from src.data.database import DatabaseManager
from src.data.loader import DataLoader
from src.data.queries import QueryEngine

__all__ = ["DatabaseManager", "DataLoader", "QueryEngine"]
