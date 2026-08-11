"""
LLM Factory — 配置驱动创建 LLM Provider 实例

新增 Provider 三步:
  1. 写 BaseLLM 子类 (如 openai_llm.py)
  2. 在 _register_providers() 中注册: LLMFactory.register_provider("openai", OpenAILLM)
  3. 在 settings.yaml 设置 llm.provider: "openai"
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from src.libs.llm.base_llm import BaseLLM

if TYPE_CHECKING:
    from src.core.settings import Settings


class LLMFactory:
    """LLM Provider 工厂

    设计模式:
    - 工厂模式 (Factory Pattern): 集中管理对象创建
    - 注册表模式 (Registry Pattern): 通过类属性字典存储 Provider
    - 配置驱动: provider 名称来自 settings.yaml
    """

    _PROVIDERS: dict[str, type[BaseLLM]] = {}

    # ------------------------------------------------------------------
    # 注册
    # ------------------------------------------------------------------

    @classmethod
    def register_provider(cls, name: str, provider_class: type[BaseLLM]) -> None:
        """注册新的 LLM Provider"""
        if not issubclass(provider_class, BaseLLM):
            raise ValueError(
                f"Provider '{provider_class.__name__}' 必须继承 BaseLLM"
            )
        cls._PROVIDERS[name.lower()] = provider_class

    # ------------------------------------------------------------------
    # 创建
    # ------------------------------------------------------------------

    @classmethod
    def create(cls, settings: Settings, **override_kwargs: Any) -> BaseLLM:
        """根据配置创建 LLM 实例

        Args:
            settings: 应用配置 (settings.llm.provider 决定选哪个)
            **override_kwargs: 可选的配置覆盖

        Returns:
            BaseLLM 实例

        Raises:
            ValueError: 未知 provider
        """
        provider_name = settings.llm.provider.lower()
        provider_class = cls._PROVIDERS.get(provider_name)

        if provider_class is None:
            available = ", ".join(sorted(cls._PROVIDERS.keys())) or "(无)"
            raise ValueError(
                f"不支持的 LLM Provider: '{provider_name}'。"
                f"可用: {available}"
            )

        try:
            return provider_class(settings=settings, **override_kwargs)
        except Exception as e:
            raise RuntimeError(
                f"创建 LLM Provider '{provider_name}' 失败: {e}"
            ) from e

    # ------------------------------------------------------------------
    # 查询
    # ------------------------------------------------------------------

    @classmethod
    def list_providers(cls) -> list[str]:
        """列出所有已注册的 Provider 名称"""
        return sorted(cls._PROVIDERS.keys())


# =========================================================================
# 模块加载时自动注册所有已实现的 Provider
# =========================================================================

def _register_providers() -> None:
    """导入并注册所有 LLM Provider 实现"""
    try:
        from src.libs.llm.deepseek_llm import DeepSeekLLM
        LLMFactory.register_provider("deepseek", DeepSeekLLM)
    except ImportError:
        pass

    try:
        from src.libs.llm.openai_llm import OpenAILLM
        LLMFactory.register_provider("openai", OpenAILLM)
    except ImportError:
        pass


_register_providers()
