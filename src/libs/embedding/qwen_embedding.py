"""
Qwen Embedding Provider (阿里云 DashScope / OpenAI SDK)

通过 OpenAI 兼容接口调用 Qwen text-embedding-v3。
限制: 单次最多 10 条文本。
"""

from __future__ import annotations

import os
from typing import Any, Optional

from openai import OpenAI

from src.libs.embedding.base_embedding import BaseEmbedding


class QwenEmbeddingError(RuntimeError):
    """Qwen Embedding API 调用失败"""


class QwenEmbedding(BaseEmbedding):
    """Qwen Embedding Provider (基于 OpenAI SDK)

    用法:
        emb = QwenEmbedding(settings)
        vectors = emb.embed(["文本1", "文本2"])
        query_vec = emb.embed_query("查询文本")
    """

    DEFAULT_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    MAX_BATCH_SIZE = 10   # Qwen API 单次上限

    def __init__(
        self,
        settings: Any,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        self._model = settings.embedding.model
        self._dimensions = settings.embedding.dimensions

        api_key = (
            api_key
            or getattr(settings.embedding, "api_key", None)
            or os.environ.get("QWEN_API_KEY", "")
        )
        if not api_key:
            raise ValueError(
                "Qwen API key 未设置。请在 settings.yaml (embedding.api_key)、"
                "QWEN_API_KEY 环境变量中配置，或传入 api_key 参数。"
            )

        self._client = OpenAI(
            api_key=api_key,
            base_url=(base_url or settings.embedding.base_url or self.DEFAULT_BASE_URL),
        )

    # ------------------------------------------------------------------
    # 核心接口
    # ------------------------------------------------------------------

    def embed(self, texts: list[str], trace: Optional[Any] = None) -> list[list[float]]:
        if not texts:
            return []

        # 超过批次上限时分批
        if len(texts) > self.MAX_BATCH_SIZE:
            result: list[list[float]] = []
            for i in range(0, len(texts), self.MAX_BATCH_SIZE):
                batch = texts[i : i + self.MAX_BATCH_SIZE]
                result.extend(self._call_api(batch))
            return result

        return self._call_api(texts)

    def embed_query(self, query: str) -> list[float]:
        results = self.embed([query])
        return results[0]

    @property
    def dimensions(self) -> int:
        return self._dimensions

    # ------------------------------------------------------------------
    # 内部
    # ------------------------------------------------------------------

    def _call_api(self, texts: list[str]) -> list[list[float]]:
        try:
            response = self._client.embeddings.create(
                model=self._model,
                input=texts,
            )
        except Exception as e:
            raise QwenEmbeddingError(f"[Qwen Embedding] API 调用失败: {e}") from e

        # 按 index 排序确保顺序一致
        items = sorted(response.data, key=lambda x: x.index)
        return [item.embedding for item in items]
