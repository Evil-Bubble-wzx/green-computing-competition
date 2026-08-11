"""
Reranker Factory — 配置驱动创建 Reranker 实例
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from src.libs.reranker.base_reranker import BaseReranker

if TYPE_CHECKING:
    from src.core.settings import Settings


class RerankerFactory:
    """Reranker Provider 工厂"""

    _PROVIDERS: dict[str, type[BaseReranker]] = {}

    @classmethod
    def register_provider(cls, name: str, provider_class: type[BaseReranker]) -> None:
        if not issubclass(provider_class, BaseReranker):
            raise ValueError(
                f"Provider '{provider_class.__name__}' 必须继承 BaseReranker"
            )
        cls._PROVIDERS[name.lower()] = provider_class

    @classmethod
    def create(cls, settings: Settings, **override_kwargs: Any) -> BaseReranker:
        provider_name = settings.retrieval.rerank.provider.lower()

        if provider_name == "none":
            from src.libs.reranker.base_reranker import BaseReranker

            class NoopReranker(BaseReranker):
                def rerank(self, query, documents, top_k=5, **kwargs):
                    return [
                        RankedDocument(content=d, score=1.0, index=i)
                        for i, d in enumerate(documents[:top_k])
                    ]

            return NoopReranker()

        provider_class = cls._PROVIDERS.get(provider_name)

        if provider_class is None:
            available = ", ".join(sorted(cls._PROVIDERS.keys())) or "none"
            raise ValueError(
                f"不支持的 Reranker Provider: '{provider_name}'。"
                f"可用: {available}"
            )

        try:
            return provider_class(settings=settings, **override_kwargs)
        except Exception as e:
            raise RuntimeError(
                f"创建 Reranker Provider '{provider_name}' 失败: {e}"
            ) from e

    @classmethod
    def list_providers(cls) -> list[str]:
        return sorted(cls._PROVIDERS.keys())


# 导入 RankedDocument 到本地作用域
from src.libs.reranker.base_reranker import RankedDocument  # noqa: E402


def _register_providers() -> None:
    try:
        from src.libs.reranker.llm_reranker import LLMReranker
        RerankerFactory.register_provider("llm", LLMReranker)
    except ImportError:
        pass


_register_providers()
