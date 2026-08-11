"""Dashboard 数据加载器"""

import streamlit as st
from pathlib import Path
from src.core.settings import load_settings
from src.data.database import DatabaseManager
from src.data.queries import QueryEngine


@st.cache_resource
def get_query_engine() -> QueryEngine:
    settings = load_settings(Path("config/settings.yaml"))
    db = DatabaseManager(settings)
    return QueryEngine(db)


def load_shared_data(qe: QueryEngine) -> dict:
    """预加载各数据页面共享的数据（聊天页不调用）"""
    return {
        "ranking_2024": qe.get_score_ranking(2024),
        "layout_summary": qe.get_layout_summary(),
        "provinces": qe.list_all_provinces(),
        "boundary": qe.get_boundary_provinces(),
        "lisa_sig": qe.get_significant_lisa(),
    }
