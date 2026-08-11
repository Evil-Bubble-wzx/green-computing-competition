"""
Web Search Factory — 配置驱动创建联网搜索 Provider 实例
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from src.libs.search.base_web_search import BaseWebSearch

if TYPE_CHECKING:
    from src.core.settings import Settings


class WebSearchFactory:
    """联网搜索 Provider 工厂"""

    _PROVIDERS: dict[str, type[BaseWebSearch]] = {}

    @classmethod
    def register_provider(cls, name: str, provider_class: type[BaseWebSearch]) -> None:
        if not issubclass(provider_class, BaseWebSearch):
            raise ValueError(
                f"Provider '{provider_class.__name__}' 必须继承 BaseWebSearch"
            )
        cls._PROVIDERS[name.lower()] = provider_class

    @classmethod
    def create(cls, settings: Settings, **override_kwargs: Any) -> BaseWebSearch:
        provider_name = settings.web_search.provider.lower()

        if provider_name == "none":
            class NoopSearch(BaseWebSearch):
                def search(self, query, max_results=5, trusted_domains=None, trace=None):
                    return []
            return NoopSearch()

        provider_class = cls._PROVIDERS.get(provider_name)

        if provider_class is None:
            available = ", ".join(sorted(cls._PROVIDERS.keys())) or "none"
            raise ValueError(
                f"不支持的 Web Search Provider: '{provider_name}'。"
                f"可用: {available}"
            )

        try:
            return provider_class(settings=settings, **override_kwargs)
        except Exception as e:
            raise RuntimeError(
                f"创建 Web Search Provider '{provider_name}' 失败: {e}"
            ) from e

    @classmethod
    def list_providers(cls) -> list[str]:
        return sorted(cls._PROVIDERS.keys())


def _register_providers() -> None:
    try:
        from src.libs.search.builtin_web_search import BuiltinWebSearch
        WebSearchFactory.register_provider("builtin", BuiltinWebSearch)
    except ImportError:
        pass


_register_providers()
