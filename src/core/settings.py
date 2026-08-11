"""
绿色算力智能决策助手 - 配置加载模块

从 YAML 配置文件加载设置，支持环境变量替换。
"""

import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

import yaml


class SettingsError(Exception):
    """配置加载错误"""
    pass


# =============================================================================
# 配置数据类 (按 config/settings.yaml 结构)
# =============================================================================

@dataclass
class DatabaseConfig:
    """PostgreSQL 连接配置"""
    host: str = "localhost"
    port: str = "5432"
    database: str = "green_computing"
    user: str = "postgres"
    password: str = ""


@dataclass
class DataConfig:
    docx_dir: str = "./docx"
    golden_set: str = "./docx/01_系统标准答案_Golden_Set.xlsx"
    core_results: str = "./docx/05_综合评价核心结果_NAT_FINAL.xlsx"
    field_dict: str = "./docx/02_系统同步关键字段字典.xlsx"
    database: DatabaseConfig = field(default_factory=DatabaseConfig)


@dataclass
class MiniMaxConfig:
    api_key: str = ""
    base_url: str = "https://api.minimax.chat/v1"
    model: str = "MiniMax-M3"


@dataclass
class LLMConfig:
    provider: str = "deepseek"
    model: str = "deepseek-chat"
    api_key: str = ""
    base_url: str = "https://api.deepseek.com/v1"
    temperature: float = 0.0
    max_tokens: int = 4096


@dataclass
class EmbeddingConfig:
    provider: str = "qwen"
    model: str = "text-embedding-v3"
    api_key: str = ""
    base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    dimensions: int = 1024


@dataclass
class VectorStoreConfig:
    provider: str = "chroma"
    persist_directory: str = "./data/db/chroma"
    collection_name: str = "proposal_knowledge"


@dataclass
class RerankConfig:
    enabled: bool = True
    provider: str = "llm"


@dataclass
class RetrievalConfig:
    db_top_k: int = 10
    vector_top_k: int = 10
    web_top_k: int = 5
    fusion_top_k: int = 8
    rrf_k: int = 60
    rerank: RerankConfig = field(default_factory=RerankConfig)


@dataclass
class WebSearchConfig:
    enabled: bool = True
    provider: str = "builtin"
    max_results: int = 5
    trusted_domains: list[str] = field(default_factory=list)


@dataclass
class IngestionConfig:
    chunk_size: int = 800
    chunk_overlap: int = 150
    splitter: str = "recursive"
    supported_formats: list[str] = field(default_factory=lambda: [".pdf", ".docx", ".txt"])


@dataclass
class ChatConfig:
    strict_numeric_mode: bool = True
    reject_out_of_scope: bool = True
    require_evidence: bool = True
    max_turns: int = 10


@dataclass
class DashboardMapConfig:
    province_name_field: str = "省份"
    china_geojson: str = "./data/china_provinces.geojson"


@dataclass
class DashboardConfig:
    title: str = "省域绿色算力承载能力评估与资源布局决策支持系统"
    data_version: str = "NAT_FINAL"
    color_scheme: str = "morandi"
    map: DashboardMapConfig = field(default_factory=DashboardMapConfig)


@dataclass
class ObservabilityConfig:
    log_level: str = "INFO"
    log_file: str = "./logs/system.log"
    trace_enabled: bool = True
    trace_file: str = "./logs/traces.jsonl"


@dataclass
class MCPConfig:
    server_name: str = "green-computing-advisor"
    server_version: str = "0.1.0"
    transport: str = "stdio"


@dataclass
class Settings:
    """总配置"""
    data: DataConfig = field(default_factory=DataConfig)
    llm: LLMConfig = field(default_factory=LLMConfig)
    minimax: MiniMaxConfig = field(default_factory=MiniMaxConfig)
    embedding: EmbeddingConfig = field(default_factory=EmbeddingConfig)
    vector_store: VectorStoreConfig = field(default_factory=VectorStoreConfig)
    retrieval: RetrievalConfig = field(default_factory=RetrievalConfig)
    web_search: WebSearchConfig = field(default_factory=WebSearchConfig)
    ingestion: IngestionConfig = field(default_factory=IngestionConfig)
    chat: ChatConfig = field(default_factory=ChatConfig)
    dashboard: DashboardConfig = field(default_factory=DashboardConfig)
    observability: ObservabilityConfig = field(default_factory=ObservabilityConfig)
    mcp: MCPConfig = field(default_factory=MCPConfig)


# =============================================================================
# 配置加载函数
# =============================================================================

_ENV_VAR_PATTERN = re.compile(r"\$\{(\w+)(?::([^}]*))?\}")


def _resolve_env_vars(value: str) -> str:
    """替换字符串中的 ${ENV_VAR} 或 ${ENV_VAR:default} 为环境变量值"""

    def _replace(match: re.Match) -> str:
        var_name = match.group(1)
        default_val = match.group(2) if match.group(2) is not None else ""
        env_val = os.environ.get(var_name)
        if env_val:
            return env_val
        if default_val:
            return default_val
        print(f"[WARNING] Environment variable '{var_name}' is not set, using empty string.")
        return ""

    return _ENV_VAR_PATTERN.sub(_replace, value)


def _resolve_dict_env(d: dict) -> dict:
    """递归解析字典中所有字符串值的环境变量"""
    result = {}
    for key, value in d.items():
        if isinstance(value, str):
            result[key] = _resolve_env_vars(value)
        elif isinstance(value, dict):
            result[key] = _resolve_dict_env(value)
        elif isinstance(value, list):
            result[key] = [
                _resolve_env_vars(v) if isinstance(v, str) else v
                for v in value
            ]
        else:
            result[key] = value
    return result


def load_settings(config_path: str | Path) -> Settings:
    """
    从 YAML 文件加载配置。

    Args:
        config_path: YAML 配置文件路径

    Returns:
        Settings 对象

    Raises:
        SettingsError: 文件不存在或格式错误
    """
    path = Path(config_path)
    if not path.exists():
        raise SettingsError(f"Configuration file not found: {config_path}")

    try:
        with open(path, "r", encoding="utf-8") as f:
            raw = yaml.safe_load(f)
    except yaml.YAMLError as e:
        raise SettingsError(f"Invalid YAML in {config_path}: {e}")

    if raw is None:
        raw = {}

    # 解析环境变量
    raw = _resolve_dict_env(raw)

    # 逐段构建配置对象
    settings = Settings()

    if "data" in raw:
        d = raw["data"]
        if "database" in d:
            d["database"] = DatabaseConfig(**d.pop("database"))
        settings.data = DataConfig(**d)

    if "llm" in raw:
        settings.llm = LLMConfig(**raw["llm"])

    if "embedding" in raw:
        settings.embedding = EmbeddingConfig(**raw["embedding"])

    if "vector_store" in raw:
        settings.vector_store = VectorStoreConfig(**raw["vector_store"])

    if "retrieval" in raw:
        r = raw["retrieval"]
        if "rerank" in r:
            settings.retrieval.rerank = RerankConfig(**r.pop("rerank"))
        settings.retrieval = RetrievalConfig(**r)

    if "web_search" in raw:
        settings.web_search = WebSearchConfig(**raw["web_search"])

    if "ingestion" in raw:
        settings.ingestion = IngestionConfig(**raw["ingestion"])

    if "chat" in raw:
        settings.chat = ChatConfig(**raw["chat"])

    if "dashboard" in raw:
        d = raw["dashboard"]
        if "map" in d:
            d["map"] = DashboardMapConfig(**d.pop("map"))
        settings.dashboard = DashboardConfig(**d)

    if "observability" in raw:
        settings.observability = ObservabilityConfig(**raw["observability"])

    if "minimax" in raw:
        settings.minimax = MiniMaxConfig(**raw["minimax"])

    if "mcp" in raw:
        settings.mcp = MCPConfig(**raw["mcp"])

    return settings
