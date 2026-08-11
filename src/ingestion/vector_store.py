"""
向量存储 — ChromaDB 封装

管理企划书文档的向量索引。
"""

from __future__ import annotations

from pathlib import Path


class ChromaVectorStore:
    """ChromaDB 向量存储

    用法:
        store = ChromaVectorStore(persist_dir="./data/db/chroma", collection="proposals")
        store.add_chunks(chunks, embeddings, metadata_list)
        results = store.search(query_vector, top_k=5)
    """

    def __init__(self, persist_dir: str | Path, collection_name: str = "proposal_knowledge"):
        import chromadb
        from chromadb.config import Settings as ChromaSettings

        persist_dir = Path(persist_dir)
        persist_dir.mkdir(parents=True, exist_ok=True)

        self._client = chromadb.PersistentClient(
            path=str(persist_dir),
            settings=ChromaSettings(anonymized_telemetry=False),
        )
        self._collection = self._client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"},
        )

    def add_chunks(
        self,
        chunk_ids: list[str],
        texts: list[str],
        embeddings: list[list[float]],
        metadatas: list[dict] | None = None,
    ):
        """批量添加文档块到向量库"""
        self._collection.add(
            ids=chunk_ids,
            documents=texts,
            embeddings=embeddings,
            metadatas=metadatas or [{}] * len(texts),
        )

    def search(
        self,
        query_embedding: list[float],
        top_k: int = 5,
        where: dict | None = None,
    ) -> list[dict]:
        """相似度搜索"""
        results = self._collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            where=where,
            include=["documents", "metadatas", "distances"],
        )
        hits = []
        if results["ids"] and results["ids"][0]:
            for i in range(len(results["ids"][0])):
                hits.append({
                    "id": results["ids"][0][i],
                    "text": results["documents"][0][i] if results["documents"] else "",
                    "metadata": results["metadatas"][0][i] if results["metadatas"] else {},
                    "distance": results["distances"][0][i] if results["distances"] else 0,
                })
        return hits

    def delete_by_source(self, source_file: str) -> int:
        """按源文件删除所有相关向量"""
        existing = self._collection.get(where={"source": source_file})
        if existing["ids"]:
            self._collection.delete(ids=existing["ids"])
            return len(existing["ids"])
        return 0

    def list_sources(self) -> list[str]:
        """列出所有已摄入的文档来源"""
        all_data = self._collection.get(include=["metadatas"])
        sources = set()
        if all_data["metadatas"]:
            for m in all_data["metadatas"]:
                if m and "source" in m:
                    sources.add(m["source"])
        return sorted(sources)

    def count(self) -> int:
        return self._collection.count()
