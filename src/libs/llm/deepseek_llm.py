"""
DeepSeek LLM Provider (OpenAI SDK)

DeepSeek 使用 OpenAI 兼容 API，通过 openai.OpenAI() 调用。
"""

from __future__ import annotations

import os
from typing import Any, Optional

from openai import OpenAI

from src.libs.llm.base_llm import BaseLLM, ChatResponse, Message, StreamChunk


class DeepSeekLLMError(RuntimeError):
    """DeepSeek API 调用失败"""


class DeepSeekLLM(BaseLLM):
    """DeepSeek LLM Provider (基于 OpenAI SDK)

    用法:
        llm = DeepSeekLLM(settings)
        resp = llm.chat([Message(role="user", content="江苏2024年综合得分？")])

        for chunk in llm.chat_stream(messages):
            print(chunk.content, end="")
    """

    DEFAULT_BASE_URL = "https://api.deepseek.com"

    def __init__(
        self,
        settings: Any,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        self.model = settings.llm.model
        self.default_temperature = settings.llm.temperature
        self.default_max_tokens = settings.llm.max_tokens

        api_key = (
            api_key
            or getattr(settings.llm, "api_key", None)
            or os.environ.get("DEEPSEEK_API_KEY", "")
        )
        if not api_key:
            raise ValueError(
                "DeepSeek API key 未设置。请在 settings.yaml (llm.api_key)、"
                "DEEPSEEK_API_KEY 环境变量中配置，或传入 api_key 参数。"
            )

        self._client = OpenAI(
            api_key=api_key,
            base_url=(base_url or settings.llm.base_url or self.DEFAULT_BASE_URL),
        )

    # ------------------------------------------------------------------
    # chat — 非流式
    # ------------------------------------------------------------------

    def chat(
        self,
        messages: list[Message],
        trace: Optional[Any] = None,
        **kwargs: Any,
    ) -> ChatResponse:
        self.validate_messages(messages)

        api_messages = [{"role": m.role, "content": m.content} for m in messages]

        try:
            response = self._client.chat.completions.create(
                model=kwargs.get("model", self.model),
                messages=api_messages,
                temperature=kwargs.get("temperature", self.default_temperature),
                max_tokens=kwargs.get("max_tokens", self.default_max_tokens),
                stream=False,
            )
        except Exception as e:
            raise DeepSeekLLMError(f"[DeepSeek] API 调用失败: {e}") from e

        choice = response.choices[0]
        return ChatResponse(
            content=choice.message.content or "",
            model=response.model,
            usage={
                "prompt_tokens": response.usage.prompt_tokens if response.usage else 0,
                "completion_tokens": response.usage.completion_tokens if response.usage else 0,
                "total_tokens": response.usage.total_tokens if response.usage else 0,
            },
            raw_response=response,
        )

    # ------------------------------------------------------------------
    # chat_stream — 流式
    # ------------------------------------------------------------------

    def chat_stream(
        self,
        messages: list[Message],
        trace: Optional[Any] = None,
        **kwargs: Any,
    ):
        self.validate_messages(messages)

        api_messages = [{"role": m.role, "content": m.content} for m in messages]

        try:
            stream = self._client.chat.completions.create(
                model=kwargs.get("model", self.model),
                messages=api_messages,
                temperature=kwargs.get("temperature", self.default_temperature),
                max_tokens=kwargs.get("max_tokens", self.default_max_tokens),
                stream=True,
            )
            for chunk in stream:
                delta = chunk.choices[0].delta if chunk.choices else None
                content = delta.content if delta and delta.content else ""
                finish = chunk.choices[0].finish_reason if chunk.choices else None
                if content:
                    yield StreamChunk(content=content, finish_reason=finish)
                elif finish:
                    yield StreamChunk(content="", finish_reason=finish)
        except Exception as e:
            raise DeepSeekLLMError(f"[DeepSeek] 流式调用失败: {e}") from e
