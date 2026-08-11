"""
Dashboard 全局样式
"""

import streamlit as st

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

html, body, [class*="css"] {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
}

/* 侧边栏 */
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0F172A 0%, #1E3A5F 100%);
}
[data-testid="stSidebar"] * { color: #E2E8F0 !important; }
[data-testid="stSidebar"] .stRadio label {
    border-radius: 8px; transition: background 0.2s; cursor: pointer;
}
[data-testid="stSidebar"] .stRadio label:hover { background: rgba(255,255,255,0.08); }
[data-testid="stSidebar"] .stButton button {
    background: rgba(255,255,255,0.12);
    border: 1px solid rgba(255,255,255,0.2);
    color: #E2E8F0;
}

/* Metric 卡片 */
[data-testid="stMetric"] {
    background: #FFFFFF;
    border-radius: 12px; padding: 16px;
    border: 1px solid #DBEAFE;
    box-shadow: 0 1px 2px rgba(0,0,0,0.04);
}
[data-testid="stMetric"] label { color: #94A3B8 !important; font-size: 11px; font-weight: 600; text-transform: uppercase; }
[data-testid="stMetric"] [data-testid="stMetricValue"] { color: #1E3A8A; font-weight: 700; font-size: 22px; }

/* 按钮 */
.stButton button {
    border-radius: 8px; background: #D97706; color: #FFFFFF; border: none;
    font-weight: 600; transition: opacity 0.2s;
}
.stButton button:hover { opacity: 0.9; }

/* 数据表 */
[data-testid="stDataFrame"] { border-radius: 10px; border: 1px solid #DBEAFE; overflow: hidden; }
[data-testid="stDataFrame"] th { background: #EFF6FF !important; color: #1E40AF !important; font-size: 12px; font-weight: 600; text-transform: uppercase; }
[data-testid="stDataFrame"] td { font-size: 13px; font-variant-numeric: tabular-nums; }
[data-testid="stDataFrame"] tbody tr:hover { background: #F8FAFC; }

[data-baseweb="select"] { border-radius: 8px !important; border-color: #E2E8F0 !important; }
[data-testid="stAlert"] { border-radius: 10px; }
[data-testid="stExpander"] { border-radius: 10px; border: 1px solid #DBEAFE; }

::-webkit-scrollbar { width: 5px; }
::-webkit-scrollbar-thumb { background: #94A3B8; border-radius: 3px; }
</style>
"""

def inject():
    st.markdown(CSS, unsafe_allow_html=True)
