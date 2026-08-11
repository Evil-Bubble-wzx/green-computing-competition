"""
Embedding Factory — 配置驱动创建 Embedding Provider 实例
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from src.libs.embedding.base_embedding import BaseEmbedding

if TYPE_CHECKING:
    from src.core.settings import Settings


class EmbeddingFactory:
    """Embedding Provider 工厂"""

    _PROVIDERS: dict[str, type[BaseEmbedding]] = {}

    @classmethod
    def register_provider(cls, name: str, provider_class: type[BaseEmbedding]) -> None:
        if not issubclass(provider_class, BaseEmbedding):
            raise ValueError(
                f"Provider '{provider_class.__name__}' 必须继承 BaseEmbedding"
            )
        cls._PROVIDERS[name.lower()] = provider_class

    @classmethod
    def create(cls, settings: Settings, **override_kwargs: Any) -> BaseEmbedding:
        provider_name = settings.embedding.provider.lower()
        provider_class = cls._PROVIDERS.get(provider_name)

        if provider_class is None:
            available = ", ".join(sorted(cls._PROVIDERS.keys())) or "(无)"
            raise ValueError(
                f"不支持的 Embedding Provider: '{provider_name}'。"
                f"可用: {available}"
            )

        try:
            return provider_class(settings=settings, **override_kwargs)
        except Exception as e:
            raise RuntimeError(
                f"创建 Embedding Provider '{provider_name}' 失败: {e}"
            ) from e

    @classmethod
    def list_providers(cls) -> list[str]:
        return sorted(cls._PROVIDERS.keys())


def _register_providers() -> None:
    """注册所有 Embedding Provider 实现"""
    try:
        from src.libs.embedding.qwen_embedding import QwenEmbedding
        EmbeddingFactory.register_provider("qwen", QwenEmbedding)
    except ImportError:
        pass


_register_providers()
