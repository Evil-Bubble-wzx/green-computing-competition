"""
LLM Provider 抽象基类

定义所有 LLM 实现的统一接口。新增 Provider 只需继承此类并实现 chat() 方法。
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Optional


@dataclass
class Message:
    """对话消息"""
    role: str       # "system" | "user" | "assistant"
    content: str


@dataclass
class ChatResponse:
    """LLM 响应"""
    content: str
    model: str
    usage: Optional[dict[str, int]] = None     # {prompt_tokens, completion_tokens, total_tokens}
    raw_response: Optional[Any] = None          # 原始响应，调试用


@dataclass
class StreamChunk:
    """流式输出的单块文本"""
    content: str            # 本次增量文本
    finish_reason: Optional[str] = None  # "stop" | "length" | None


class BaseLLM(ABC):
    """LLM Provider 抽象基类

    设计原则:
    - 可插拔: 子类可自由替换，不影响上游调用代码
    - 配置驱动: 通过 Factory + settings.yaml 切换
    - 输入校验: 基类提供 validate_messages()
    - 流式优先: chat_stream() 默认 fallback 到 chat()，子类可覆盖
    """

    @abstractmethod
    def chat(
        self,
        messages: list[Message],
        trace: Optional[Any] = None,
        **kwargs: Any,
    ) -> ChatResponse:
        """生成对话回复（非流式）

        Args:
            messages: 对话消息列表
            trace: 可选 TraceContext (Stage F 接入)
            **kwargs: provider 特定参数 (temperature, max_tokens ...)

        Returns:
            ChatResponse (含 content, model, usage)
        """
        ...

    def chat_stream(
        self,
        messages: list[Message],
        trace: Optional[Any] = None,
        **kwargs: Any,
    ):
        """流式生成对话回复（生成器）

        子类应覆盖此方法以支持真正的流式输出。
        默认实现 fallback 到 chat()，将完整结果作为一个 chunk 返回。

        Yields:
            StreamChunk: 逐块的文本增量
        """
        response = self.chat(messages, trace=trace, **kwargs)
        yield StreamChunk(content=response.content, finish_reason="stop")

    def validate_messages(self, messages: list[Message]) -> None:
        """校验消息列表结构"""
        if not messages:
            raise ValueError("消息列表不能为空")
        valid_roles = {"system", "user", "assistant"}
        for i, msg in enumerate(messages):
            if not isinstance(msg, Message):
                raise ValueError(f"消息 [{i}] 不是 Message 实例")
            if msg.role not in valid_roles:
                raise ValueError(f"消息 [{i}] 角色无效: '{msg.role}'")
            if not msg.content or not msg.content.strip():
                raise ValueError(f"消息 [{i}] 内容为空")
