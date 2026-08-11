"""
Streamlit Dashboard 入口 — st.navigation 原生多页隔离
"""

import streamlit as st
from pathlib import Path
from src.dashboard.styles import inject

HERE = Path(__file__).resolve().parent
PAGES = HERE / "pages"


def main():
    st.set_page_config(
        page_title="绿色算力智能决策助手",
        page_icon="🌿",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    inject()

    pg = st.navigation([
        st.Page(str(PAGES / "overview.py"), title="系统总览", icon="📊"),
        st.Page(str(PAGES / "province.py"), title="省份诊断", icon="🏙️"),
        st.Page(str(PAGES / "comparison.py"), title="多省对比", icon="🔄"),
        st.Page(str(PAGES / "spatial.py"), title="空间分析", icon="🗺️"),
        st.Page(str(PAGES / "layout_page.py"), title="布局决策", icon="📐"),
        st.Page(str(PAGES / "chat_page.py"), title="智能问答", icon="💬"),
    ])
    pg.run()


if __name__ == "__main__":
    main()
