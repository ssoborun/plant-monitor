import streamlit as st
import pandas as pd
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.bigquery_client import get_readings, get_latest_reading
from utils.ai_helpers import analyze_data_with_ai, text_to_speech, generate_sensor_summary
from utils.weather import get_current_weather

st.set_page_config(page_title="Plant Monitor — AI Assistant", page_icon="🤖", layout="wide")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');
html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
[data-testid="stSidebar"] { background: #0d1117 !important; border-right: 1px solid #21262d; }
[data-testid="stSidebar"] * { color: #c9d1d9 !important; }
.section-title {
    font-size: 0.65rem; font-weight: 700; text-transform: uppercase;
    letter-spacing: 0.2em; margin-bottom: 14px; padding-bottom: 8px;
    border-bottom: 1px solid rgba(128,128,128,0.12); color: #2563eb;
}
.chat-user {
    border-radius: 12px 12px 0 12px; padding: 12px 16px; margin: 10px 0 4px 0;
    border: 1px solid rgba(37,99,235,0.2); background: rgba(37,99,235,0.04);
}
.chat-ai {
    border-radius: 0 12px 12px 12px; padding: 12px 16px; margin: 4px 0 10px 0;
    border: 1px solid rgba(22,163,74,0.2); background: rgba(22,163,74,0.04);
}
.chat-label { font-size: 0.65rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.1em; margin-bottom: 6px; }
.label-user { color: #2563eb; }
.label-ai   { color: #16a34a; }
hr { border-color: rgba(128,128,128,0.1) !important; margin: 20px 0 !important; }
</style>
""", unsafe_allow_html=True)

st.markdown("## 🤖 AI Assistant")
st.caption("Ask questions about your sensor data — powered by Claude AI with Google TTS")
st.markdown("---")

# ── Data selection ────────────────────────────────────────────────────────────
st.markdown('<div class="section-title">Select Data Period</div>', unsafe_allow_html=True)
c1, c2 = st.columns(2)
with c1: start_date = st.date_input("From", value=pd.Timestamp.now() - pd.Timedelta(days=7))
with c2: end_date   = st.date_input("To",   value=pd.Timestamp.now())

if st.button("Load Data for Analysis", type="primary"):
    with st.spinner("Loading data from BigQuery..."):
        start_dt = pd.Timestamp(start_date).tz_localize("UTC")
        end_dt   = pd.Timestamp(end_date).replace(hour=23, minute=59, second=59).tz_localize("UTC")
        df = get_readings(start_date=start_dt, end_date=end_dt, limit=2000)
        st.session_state["ai_df"] = df
        if not df.empty:
            st.success(f"Loaded {len(df):,} readings from {start_date} to {end_date}")
        else:
            st.warning("No data found for this period.")

if "ai_df" not in st.session_state:
    st.info("Load a data period first, then ask your question.")
    st.stop()

df = st.session_state["ai_df"]
st.caption(f"Working with **{len(df):,} readings** — {start_date} → {end_date}")
st.markdown("---")

# ── Chat interface ────────────────────────────────────────────────────────────
st.markdown('<div class="section-title">Ask a Question</div>', unsafe_allow_html=True)

if "chat_history"      not in st.session_state: st.session_state["chat_history"] = []
if "current_question"  not in st.session_state: st.session_state["current_question"] = ""

QUICK_QS = [
    "What was the average temperature for this period?",
    "Did humidity drop below 40% at any point?",
    "What trend do you see in the soil moisture data?",
    "Were there any anomalies in the sensor data?",
    "Compare temperature and humidity patterns",
]

st.markdown("**Quick questions:**")
qcols = st.columns(len(QUICK_QS))
for i, q in enumerate(QUICK_QS):
    with qcols[i]:
        if st.button(q[:28] + "…", key=f"q_{i}", help=q):
            with st.spinner("Analyzing…"):
                answer = analyze_data_with_ai(df, q)
            st.session_state["chat_history"].append({"question": q, "answer": answer})
            st.rerun()

user_input = st.text_area("Or type your question:", value=st.session_state["current_question"],
    placeholder="e.g. What was the humidity trend this week?", height=80)

a1, a2 = st.columns([3, 1])
with a1: send  = st.button("Ask AI", type="primary", disabled=not user_input.strip())
with a2: clear = st.button("Clear chat")

if clear:
    st.session_state["chat_history"] = []
    st.rerun()

if send and user_input.strip():
    with st.spinner("Analyzing data…"):
        answer = analyze_data_with_ai(df, user_input.strip())
    st.session_state["chat_history"].append({"question": user_input.strip(), "answer": answer})

if st.session_state["chat_history"]:
    st.markdown("---")
    st.markdown('<div class="section-title">Conversation</div>', unsafe_allow_html=True)
    for i, exchange in enumerate(reversed(st.session_state["chat_history"])):
        st.markdown(f'<div class="chat-user"><div class="chat-label label-user">You</div>{exchange["question"]}</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="chat-ai"><div class="chat-label label-ai">AI Assistant</div>{exchange["answer"]}</div>', unsafe_allow_html=True)
        with st.columns([1, 4])[0]:
            if st.button("🔊 Read aloud", key=f"tts_{i}"):
                with st.spinner("Generating audio…"):
                    audio = text_to_speech(exchange["answer"])
                    if audio:
                        st.audio(audio, format="audio/mp3")
                    else:
                        st.error("TTS unavailable.")

st.markdown("---")

# ── Auto Summary ──────────────────────────────────────────────────────────────
st.markdown('<div class="section-title">Auto Summary</div>', unsafe_allow_html=True)
st.caption("Generate a spoken summary of current conditions using Google TTS")

if st.button("🔊 Generate & Read Summary"):
    latest  = get_latest_reading()
    weather = get_current_weather()
    summary = generate_sensor_summary(latest, weather)
    st.info(f"**Summary:** {summary}")
    with st.spinner("Generating audio…"):
        audio = text_to_speech(summary)
        if audio:
            st.audio(audio, format="audio/mp3")
        else:
            st.error("TTS unavailable.")