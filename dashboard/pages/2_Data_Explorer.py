import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import numpy as np
import io
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.bigquery_client import get_readings, delete_readings

st.set_page_config(page_title="Plant Monitor — Data Explorer", page_icon="🔍", layout="wide")

SWISS_OFFSET = pd.Timedelta(hours=2)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');
html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
[data-testid="stSidebar"] { background: #0d1117 !important; border-right: 1px solid #21262d; }
[data-testid="stSidebar"] * { color: #c9d1d9 !important; }
div[data-testid="stMetric"] {
    border-radius: 12px; padding: 18px 16px;
    border: 1px solid rgba(128,128,128,0.15);
    box-shadow: 0 1px 8px rgba(0,0,0,0.05);
}
div[data-testid="stMetric"] label,
div[data-testid="stMetric"] [data-testid="stMetricLabel"] p {
    font-size: 0.68rem !important; font-weight: 700 !important;
    text-transform: uppercase; letter-spacing: 0.12em; opacity: 0.5;
}
div[data-testid="stMetric"] [data-testid="stMetricValue"] {
    font-size: 1.5rem !important; font-weight: 600 !important;
    font-family: 'JetBrains Mono', monospace !important;
}
.section-title {
    font-size: 0.65rem; font-weight: 700; text-transform: uppercase;
    letter-spacing: 0.2em; margin-bottom: 14px; padding-bottom: 8px;
    border-bottom: 1px solid rgba(128,128,128,0.12); color: #2563eb;
}
hr { border-color: rgba(128,128,128,0.1) !important; margin: 20px 0 !important; }
</style>
""", unsafe_allow_html=True)

st.markdown("## 🔍 Data Explorer")
st.caption("Filter, explore, and export your raw sensor data")
st.markdown("---")

# ── Filters ───────────────────────────────────────────────────────────────────
c1, c2 = st.columns(2)
with c1:
    start_date = st.date_input("Start date", value=pd.Timestamp.now() - pd.Timedelta(days=7))
    start_hour = st.slider("Start hour", 0, 23, 0)
with c2:
    end_date = st.date_input("End date", value=pd.Timestamp.now())
    end_hour = st.slider("End hour", 0, 23, 23)

c3, _ = st.columns([2, 1])
with c3:
    limit = st.number_input("Max rows", min_value=100, max_value=10000, value=1000, step=100)

start_dt = (pd.Timestamp(start_date).replace(hour=start_hour) - SWISS_OFFSET).tz_localize("UTC")
end_dt   = (pd.Timestamp(end_date).replace(hour=end_hour, minute=59, second=59) - SWISS_OFFSET).tz_localize("UTC")

b1, b2 = st.columns([2, 1])
with b1: load    = st.button("Load Data", type="primary")
with b2: refresh = st.button("↻ Refresh")

if load or refresh:
    with st.spinner("Fetching data from BigQuery..."):
        df = get_readings(start_date=start_dt, end_date=end_dt, limit=limit)
        if not df.empty and "timestamp" in df.columns:
            df["timestamp"] = (df["timestamp"] + SWISS_OFFSET).dt.tz_localize(None)
        st.session_state["explorer_df"] = df

if "explorer_df" not in st.session_state:
    st.info("Select a date range and click Load Data.")
    st.stop()

df = st.session_state["explorer_df"]
if df.empty:
    st.warning("No data found for the selected period.")
    st.stop()

st.markdown("---")

# ── Summary ───────────────────────────────────────────────────────────────────
st.markdown('<div class="section-title">Period Summary</div>', unsafe_allow_html=True)
c1, c2, c3, c4, c5 = st.columns(5)
with c1: st.metric("Total Readings", f"{len(df):,}")
with c2:
    if "temperature" in df.columns: st.metric("Avg Temp", f"{df['temperature'].mean():.1f} °C")
with c3:
    if "humidity" in df.columns: st.metric("Avg Humidity", f"{df['humidity'].mean():.1f} %")
with c4:
    if "soil_raw" in df.columns: st.metric("Avg Soil Raw", f"{df['soil_raw'].mean():.0f}")
with c5:
    if "pressure" in df.columns: st.metric("Avg Pressure", f"{df['pressure'].mean():.1f} hPa")

st.markdown("---")

# ── Table ─────────────────────────────────────────────────────────────────────
st.markdown('<div class="section-title">Raw Data Table</div>', unsafe_allow_html=True)

all_cols = list(df.columns)
selected_cols = st.multiselect("Columns", options=all_cols, default=all_cols)
disp = df[selected_cols].reset_index(drop=True)
st.dataframe(disp, use_container_width=True, height=380)
st.caption(f"{len(disp):,} rows — times in Swiss time (UTC+2)")

st.markdown("---")

# ── Visualization ─────────────────────────────────────────────────────────────
st.markdown('<div class="section-title">Visualization</div>', unsafe_allow_html=True)

def insert_gaps(df_in, metrics):
    df_s = df_in.sort_values("timestamp").copy()
    if len(df_s) < 2: return df_s
    median_iv = df_s["timestamp"].diff().dropna().median()
    threshold = median_iv * 3
    rows = []
    for i in range(len(df_s)):
        rows.append(df_s.iloc[i])
        if i < len(df_s) - 1:
            if df_s["timestamp"].iloc[i+1] - df_s["timestamp"].iloc[i] > threshold:
                nan_row = {col: np.nan for col in df_s.columns}
                nan_row["timestamp"] = df_s["timestamp"].iloc[i] + median_iv
                rows.append(pd.Series(nan_row))
    return pd.DataFrame(rows).reset_index(drop=True)

numeric_cols = df.select_dtypes(include="number").columns.tolist()
if numeric_cols and "timestamp" in df.columns:
    selected_metrics = st.multiselect("Metrics to plot", options=numeric_cols, default=[numeric_cols[0]])
    COLORS = ["#f97316", "#3b82f6", "#22c55e", "#a855f7", "#f59e0b"]

    if selected_metrics:
        df_g = insert_gaps(df, selected_metrics)
        CHART = dict(template="plotly_white", paper_bgcolor="rgba(0,0,0,0)",
                     plot_bgcolor="rgba(0,0,0,0)", height=380,
                     font=dict(family="Inter, sans-serif", size=11),
                     xaxis=dict(showgrid=True, gridcolor="rgba(0,0,0,0.05)", zeroline=False),
                     yaxis=dict(showgrid=True, gridcolor="rgba(0,0,0,0.05)", zeroline=False))

        if len(selected_metrics) == 2:
            m1, m2 = selected_metrics
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=df_g["timestamp"], y=df_g[m1], name=m1,
                line=dict(color=COLORS[0], width=2), connectgaps=False, yaxis="y1"))
            fig.add_trace(go.Scatter(x=df_g["timestamp"], y=df_g[m2], name=m2,
                line=dict(color=COLORS[1], width=2), connectgaps=False, yaxis="y2"))
            fig.update_layout(title=f"{m1} vs {m2}",
                yaxis=dict(title=m1, color=COLORS[0], showgrid=True, gridcolor="rgba(0,0,0,0.05)"),
                yaxis2=dict(title=m2, color=COLORS[1], overlaying="y", side="right"),
                legend=dict(x=0.01, y=0.99),
                template="plotly_white", paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)", height=380,
                font=dict(family="Inter, sans-serif", size=11))
            st.caption("Dual Y-axis — each metric has its own scale")
        else:
            fig = go.Figure()
            for i, m in enumerate(selected_metrics):
                fig.add_trace(go.Scatter(x=df_g["timestamp"], y=df_g[m], name=m,
                    line=dict(color=COLORS[i % len(COLORS)], width=2), connectgaps=False))
            fig.update_layout(title="Sensor metrics over time", xaxis_title="Time", **CHART)
        st.plotly_chart(fig, use_container_width=True)

st.markdown("---")

# ── Export ────────────────────────────────────────────────────────────────────
st.markdown('<div class="section-title">Export Data</div>', unsafe_allow_html=True)

e1, e2 = st.columns(2)
with e1:
    buf = io.StringIO()
    df.to_csv(buf, index=False)
    st.download_button("Export as CSV", data=buf.getvalue(),
        file_name=f"sensor_data_{start_date}_{end_date}.csv", mime="text/csv", type="primary")
with e2:
    xbuf = io.BytesIO()
    with pd.ExcelWriter(xbuf, engine="openpyxl") as w:
        df_x = df.copy()
        if "timestamp" in df_x.columns:
            try: df_x["timestamp"] = df_x["timestamp"].dt.tz_localize(None)
            except: pass
        df_x.to_excel(w, index=False, sheet_name="Sensor Data")
        df.describe().to_excel(w, sheet_name="Statistics")
    xbuf.seek(0)
    st.download_button("Export as Excel", data=xbuf.getvalue(),
        file_name=f"sensor_data_{start_date}_{end_date}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

st.markdown("---")
with st.expander("⚠ Delete Data (use with caution)"):
    st.warning("This will permanently delete data from BigQuery.")
    if st.text_input("Type DELETE to confirm:") == "DELETE":
        if st.button("Delete selected period", type="secondary"):
            with st.spinner("Deleting..."):
                n = delete_readings(start_dt, end_dt)
                st.success(f"Deleted {n} rows")
                st.session_state.pop("explorer_df", None)