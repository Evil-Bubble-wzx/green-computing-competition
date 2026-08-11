"""智能问答"""
import tempfile
from pathlib import Path

import streamlit as st
from src.dashboard.data_loader import get_query_engine
from src.core.settings import load_settings
from src.libs.llm.llm_factory import LLMFactory
from src.libs.embedding.embedding_factory import EmbeddingFactory
from src.retrieval.hybrid_search import HybridSearcher
from src.chat.engine import ChatEngine
from src.ingestion.vector_store import ChromaVectorStore
from src.ingestion.pipeline import IngestionPipeline

qe = get_query_engine()


@st.cache_resource
def _get_engine():
    settings = load_settings("config/settings.yaml")
    llm = LLMFactory.create(settings)
    embedding = EmbeddingFactory.create(settings)
    vs = ChromaVectorStore(
        persist_dir=settings.vector_store.persist_directory,
        collection_name=settings.vector_store.collection_name,
    )
    searcher = HybridSearcher(query_engine=qe, vector_store=vs, embedding=embedding)
    return ChatEngine(llm, searcher)


@st.cache_resource
def _get_pipeline():
    settings = load_settings("config/settings.yaml")
    embedding = EmbeddingFactory.create(settings)
    vs = ChromaVectorStore(
        persist_dir=settings.vector_store.persist_directory,
        collection_name=settings.vector_store.collection_name,
    )
    return IngestionPipeline(embedding, vs,
                             chunk_size=settings.ingestion.chunk_size,
                             chunk_overlap=settings.ingestion.chunk_overlap)


st.title("💬 智能问答")
st.caption("基于 NAT_FINAL — 所有数值来自数据库")

mode_str = st.radio("模式", ["📊 数据查询", "📄 企划书咨询"], horizontal=True)
mode = "proposal_consult" if "企划书" in mode_str else "data_query"

# ── 企划书模式：PDF 上传 ──
if mode == "proposal_consult":
    pipeline = _get_pipeline()
    docs = pipeline.list_documents()

    c1, c2 = st.columns([3, 1])
    with c1:
        uploaded = st.file_uploader(
            "上传企划书 PDF",
            type=["pdf"],
            help="上传后将自动解析并向量化",
            label_visibility="collapsed",
        )
    with c2:
        if docs:
            st.caption(f"已上传 {len(docs)} 份文档")

    if uploaded and ("ingested_files" not in st.session_state):
        st.session_state.ingested_files = set()

    if uploaded and uploaded.name not in st.session_state.get("ingested_files", set()):
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp.write(uploaded.read())
            tmp_path = tmp.name
        with st.spinner(f"正在解析 {uploaded.name}…"):
            try:
                result = pipeline.ingest(tmp_path)
                Path(tmp_path).unlink()
                if result.status == "success":
                    st.session_state.ingested_files.add(uploaded.name)
                    st.success(f"✅ {uploaded.name} 已就绪 ({result.pages} 页)")
                    st.rerun()
                else:
                    st.error(f"摄入失败: {result.error}")
            except Exception as exc:
                st.error(f"摄入出错: {exc}")

    if docs:
        with st.expander(f"📋 已上传文档 ({len(docs)})"):
            for d in docs:
                c1, c2 = st.columns([5, 1])
                c1.caption(f"📄 {d}")
                if c2.button("🗑️", key=f"del_{d}"):
                    pipeline.delete_document(d)
                    st.rerun()
    st.divider()

# ── 对话 ──
if "msgs" not in st.session_state:
    st.session_state.msgs = []

for m in st.session_state.msgs:
    if m and isinstance(m, dict):
        with st.chat_message(m.get("role", "user")):
            st.markdown(m.get("content", ""))

placeholder = "输入问题…" if mode == "data_query" else "输入关于企划书的问题"
prompt = st.chat_input(placeholder)
if not prompt:
    if st.session_state.msgs and st.button("🗑️ 清空对话"):
        st.session_state.msgs = []
        st.rerun()
    st.stop()

st.chat_message("user").markdown(prompt)
st.session_state.msgs.append({"role": "user", "content": prompt})

with st.chat_message("assistant"):
    with st.spinner("思考中…"):
        try:
            engine = _get_engine()
            resp = engine.chat(prompt, mode=mode)
            answer = resp.answer if resp and resp.answer else ""
            st.markdown(answer)
            evidence = resp.evidence if resp and resp.evidence else []
            if evidence:
                with st.expander("📎 数据来源"):
                    for e in evidence[:5]:
                        if e:
                            src = e.get("source", "?") or "?"
                            title = e.get("title", "") or ""
                            snip = (e.get("snippet", "") or "")[:150]
                            st.caption(f"**[{src}]** {title}: {snip}")
            st.session_state.msgs.append({"role": "assistant", "content": answer})
        except Exception as exc:
            import traceback
            st.error(f"AI 引擎暂时不可用：{exc}")
            st.code(traceback.format_exc())
