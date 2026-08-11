"""
数据库连接管理

使用 SQLAlchemy + PostgreSQL。
通过 settings.yaml 中的 data.database 配置连接。
"""

from __future__ import annotations

from sqlalchemy import create_engine, Engine
from sqlalchemy.orm import Session, sessionmaker


class DatabaseManager:
    """
    PostgreSQL 数据库管理器。

    用法:
        db = DatabaseManager(settings)
        db.initialize()              # 创建所有表
        with db.session() as sess:   # 获取会话
            ...
    """

    def __init__(self, settings):
        """
        Args:
            settings: 应用配置对象 (settings.data.database 提供连接参数)
        """
        cfg = settings.data.database
        self._db_url = (
            f"postgresql://{cfg.user}:{cfg.password}"
            f"@{cfg.host}:{cfg.port}/{cfg.database}"
        )
        self._engine: Engine | None = None
        self._session_factory: sessionmaker | None = None

    @property
    def engine(self) -> Engine:
        if self._engine is None:
            self._engine = create_engine(
                self._db_url,
                echo=False,
                pool_size=5,
                max_overflow=10,
                pool_pre_ping=True,     # 连接前检测有效性
            )
        return self._engine

    def initialize(self) -> None:
        """创建所有 ORM 模型对应的表"""
        from src.data import models  # noqa: F401 触发模型注册
        models.Base.metadata.create_all(self.engine)

    def session(self) -> Session:
        """获取一个新的数据库会话 (需手动关闭)"""
        if self._session_factory is None:
            self._session_factory = sessionmaker(bind=self.engine)
        return self._session_factory()

    @property
    def db_url(self) -> str:
        """返回数据库连接 URL（隐藏密码）"""
        cfg = self._engine.url if self._engine else None
        if cfg:
            return f"postgresql://{cfg.username}:***@{cfg.host}:{cfg.port}/{cfg.database}"
        return self._db_url.replace(
            self._db_url.split("@")[0].split(":")[-1], "***"
        )

    def close(self) -> None:
        """释放连接池"""
        if self._engine is not None:
            self._engine.dispose()
            self._engine = None
            self._session_factory = None
