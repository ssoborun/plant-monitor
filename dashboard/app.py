import streamlit as st

st.set_page_config(
    page_title="Plant Monitor Dashboard",
    page_icon="🌱",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #1a1a2e 0%, #16213e 100%);
    }
    [data-testid="stSidebar"] * {
        color: #e0e0e0 !important;
    }
    .metric-card {
        background: linear-gradient(135deg, #1e3a5f, #0f2d4a);
        border-radius: 12px;
        padding: 20px;
        border: 1px solid #2a5a8f;
        text-align: center;
    }
    .metric-value {
        font-size: 2.2rem;
        font-weight: 700;
        color: #4fc3f7;
    }
    .metric-label {
        font-size: 0.85rem;
        color: #90a4ae;
        text-transform: uppercase;
        letter-spacing: 1px;
    }
    .alert-box {
        padding: 12px 16px;
        border-radius: 8px;
        margin: 6px 0;
        font-weight: 500;
    }
    .alert-warning {
        background: rgba(255, 193, 7, 0.15);
        border-left: 4px solid #ffc107;
        color: #ffd54f;
    }
    .alert-danger {
        background: rgba(244, 67, 54, 0.15);
        border-left: 4px solid #f44336;
        color: #ef9a9a;
    }
    .alert-success {
        background: rgba(76, 175, 80, 0.15);
        border-left: 4px solid #4caf50;
        color: #a5d6a7;
    }
    div[data-testid="stMetric"] {
        background: linear-gradient(135deg, #1e3a5f, #0f2d4a);
        border-radius: 12px;
        padding: 16px;
        border: 1px solid #2a5a8f;
    }
</style>
""", unsafe_allow_html=True)

st.markdown("# 🌱 Plant & Environment Monitor")
st.markdown("### IoT Experimentation Platform")
st.markdown("---")

col1, col2, col3 = st.columns(3)
with col1:
    st.info("📊 **Dashboard** — Live data & charts")
with col2:
    st.info("🔍 **Data Explorer** — Filter, export, analyze")
with col3:
    st.info("🤖 **AI Assistant** — Ask questions about your data")

st.markdown("---")
st.markdown("""
**How to use this platform:**
1. Connect your sensors and let the M5Stack collect data
2. Go to **Dashboard** to see live readings and trends
3. Use **Data Explorer** to filter by date and export your data
4. Ask the **AI Assistant** questions about your experiments
5. Check **Alerts** to monitor thresholds
""")

st.sidebar.markdown("## 🌱 Plant Monitor")
st.sidebar.markdown("---")
st.sidebar.markdown("Navigate using the pages above.")
st.sidebar.markdown("---")
st.sidebar.markdown("**Project:** IoT Experimentation Platform")
st.sidebar.markdown("**Device:** M5Stack Core2")
st.sidebar.markdown("**Cloud:** Google BigQuery")
