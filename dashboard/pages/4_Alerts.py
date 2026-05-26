import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.bigquery_client import get_readings, get_latest_reading
from utils.weather import get_current_weather, get_weather_alerts

st.set_page_config(page_title="Plant Monitor — Alerts", page_icon="⚡", layout="wide")

SWISS_OFFSET = pd.Timedelta(hours=2)

# ── CSS alertes + seuils ───────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');
html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
[data-testid="stSidebar"] { background: #0d1117 !important; border-right: 1px solid #21262d; }
[data-testid="stSidebar"] * { color: #c9d1d9 !important; }
div[data-testid="stMetric"] { border-radius: 12px; padding: 18px 16px; border: 1px solid rgba(128,128,128,0.15); box-shadow: 0 1px 8px rgba(0,0,0,0.05); }
div[data-testid="stMetric"] label, div[data-testid="stMetric"] [data-testid="stMetricLabel"] p { font-size: 0.68rem !important; font-weight: 700 !important; text-transform: uppercase; letter-spacing: 0.12em; opacity: 0.5; }
div[data-testid="stMetric"] [data-testid="stMetricValue"] { font-size: 1.5rem !important; font-weight: 600 !important; font-family: 'JetBrains Mono', monospace !important; }
.section-title { font-size: 0.65rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.2em; margin-bottom: 14px; padding-bottom: 8px; border-bottom: 1px solid rgba(128,128,128,0.12); color: #2563eb; }
.alert-box     { padding: 10px 14px; border-radius: 8px; margin: 5px 0; font-size: 0.85rem; font-weight: 500; }
.alert-warning { background: rgba(245,158,11,0.08); border: 1px solid rgba(245,158,11,0.25); color: #92400e; }
.alert-danger  { background: rgba(239,68,68,0.08);  border: 1px solid rgba(239,68,68,0.25);  color: #991b1b; }
.alert-success { background: rgba(34,197,94,0.08);  border: 1px solid rgba(34,197,94,0.2);   color: #166534; }
.alert-info    { background: rgba(37,99,235,0.08);  border: 1px solid rgba(37,99,235,0.2);   color: #1e40af; }
.threshold-card { border-radius: 12px; padding: 16px; border: 1px solid rgba(128,128,128,0.15); box-shadow: 0 1px 6px rgba(0,0,0,0.04); margin-bottom: 12px; }
hr { border-color: rgba(128,128,128,0.1) !important; margin: 20px 0 !important; }
</style>
""", unsafe_allow_html=True)

st.markdown("## ⚡ Alerts & Thresholds")
st.caption("Monitor your environment and configure alert thresholds")
st.markdown("---")

# ── Sélection des capteurs actifs ─────────────────────────────────────────────
st.markdown('<div class="section-title">Sensors to Monitor</div>', unsafe_allow_html=True)
sensors = st.multiselect("Active sensors",
    options=["Temperature", "Humidity", "Soil Raw", "Pressure"],
    default=["Temperature", "Humidity"])

st.markdown("---")

# ── Configuration des seuils min/max par capteur ──────────────────────────────
st.markdown('<div class="section-title">Threshold Configuration</div>', unsafe_allow_html=True)

# Valeurs par défaut pour chaque capteur
THRESHOLD_DEFAULTS = {
    "Temperature": dict(col="temperature", unit="°C",  color="#f97316", min_v=(-10,25,15), max_v=(20,50,30)),
    "Humidity":    dict(col="humidity",    unit="%",   color="#3b82f6", min_v=(10,60,35),  max_v=(50,100,70)),
    "Soil Raw":    dict(col="soil_raw",    unit="ADC", color="#22c55e", min_v=(500,2000,1000), max_v=(1500,4000,2500)),
    "Pressure":    dict(col="pressure",    unit="hPa", color="#a855f7", min_v=(950,1010,980),  max_v=(1010,1050,1030)),
}

# Stocke les seuils choisis par l'utilisateur
thresholds = {}
if sensors:
    for col_st, sensor in zip(st.columns(min(len(sensors), 2)) * 4, sensors):
        cfg = THRESHOLD_DEFAULTS[sensor]
        with col_st:
            st.markdown('<div class="threshold-card">', unsafe_allow_html=True)
            st.markdown(f"**{sensor}**")
            lo = st.slider(f"Min ({cfg['unit']})", *cfg["min_v"], key=f"min_{sensor}")
            hi = st.slider(f"Max ({cfg['unit']})", *cfg["max_v"], key=f"max_{sensor}")
            thresholds[sensor] = (lo, hi)
            st.markdown('</div>', unsafe_allow_html=True)
else:
    st.info("Select at least one sensor above.")

st.markdown("---")

# ── Alertes en temps réel ─────────────────────────────────────────────────────
st.markdown('<div class="section-title">Current Alerts</div>', unsafe_allow_html=True)

latest  = get_latest_reading()
weather = get_current_weather()
alerts  = []

if latest and sensors:
    vals = {
        "Temperature": latest.get("temperature"),
        "Humidity":    latest.get("humidity"),
        "Soil Raw":    latest.get("soil_raw"),
        "Pressure":    latest.get("pressure"),
    }
    # Niveaux d'alerte par capteur
    levels = {"Temperature": "danger", "Humidity": "warning", "Soil Raw": "warning", "Pressure": "info"}

    for sensor in sensors:
        v = vals.get(sensor)
        if v is None or sensor not in thresholds:
            continue
        lo, hi = thresholds[sensor]
        cfg = THRESHOLD_DEFAULTS[sensor]
        if v < lo:
            alerts.append((levels[sensor], f"{sensor} too low: {v:.1f}{cfg['unit']} (min {lo}{cfg['unit']})"))
        elif v > hi:
            alerts.append((levels[sensor], f"{sensor} too high: {v:.1f}{cfg['unit']} (max {hi}{cfg['unit']})"))

# Alertes météo externes (OpenWeatherMap)
if weather:
    for wa in get_weather_alerts(weather):
        alerts.append((wa["type"], wa["msg"]))

if alerts:
    for level, msg in alerts:
        st.markdown(f'<div class="alert-box alert-{level}">{msg}</div>', unsafe_allow_html=True)
else:
    st.markdown('<div class="alert-box alert-success">✓ All conditions within normal thresholds</div>', unsafe_allow_html=True)

st.markdown("---")

# ── Analyse historique des violations ────────────────────────────────────────
st.markdown('<div class="section-title">Historical Violations</div>', unsafe_allow_html=True)

c1, c2 = st.columns(2)
with c1:
    start_date = st.date_input("From", value=pd.Timestamp.now() - pd.Timedelta(days=7))
    start_hour = st.slider("Start hour", 0, 23, 0)
with c2:
    end_date = st.date_input("To", value=pd.Timestamp.now())
    end_hour = st.slider("End hour", 0, 23, 23)

start_dt = (pd.Timestamp(start_date).replace(hour=start_hour) - SWISS_OFFSET).tz_localize("UTC")
end_dt   = (pd.Timestamp(end_date).replace(hour=end_hour, minute=59, second=59) - SWISS_OFFSET).tz_localize("UTC")

if st.button("Analyze violations", type="primary"):
    with st.spinner("Loading data…"):
        df = get_readings(start_date=start_dt, end_date=end_dt, limit=5000)

    if df.empty:
        st.warning("No data found for the selected period.")
    else:
        ts_min = pd.Timestamp(df["timestamp"].min())
        ts_max = pd.Timestamp(df["timestamp"].max())
        st.caption(f"Data: {ts_min.strftime('%Y-%m-%d %H:%M')} → {ts_max.strftime('%Y-%m-%d %H:%M')} — {len(df):,} readings")

        # Compte les violations par capteur
        violations = []
        for sensor in sensors:
            cfg = THRESHOLD_DEFAULTS[sensor]
            if cfg["col"] not in df.columns or sensor not in thresholds:
                continue
            lo, hi = thresholds[sensor]
            count = len(df[(df[cfg["col"]] < lo) | (df[cfg["col"]] > hi)])
            violations.append((sensor, count))

        if violations:
            for col_st, (name, count) in zip(st.columns(len(violations)), violations):
                with col_st:
                    icon = "🔴" if count > 10 else ("🟡" if count > 0 else "🟢")
                    st.metric(f"{icon} {name}", f"{count:,} violations")

        # Config commune aux graphiques
        CHART = dict(
            template="plotly_white", paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)", height=320,
            margin=dict(l=40, r=60, t=36, b=36),
            font=dict(family="Inter, sans-serif", size=11),
            xaxis=dict(showgrid=True, gridcolor="rgba(0,0,0,0.05)"),
            yaxis=dict(showgrid=True, gridcolor="rgba(0,0,0,0.05)"),
        )

        df_s = df.sort_values("timestamp")

        # Graphique vue d'ensemble (tous les capteurs superposés, double axe Y)
        sel = [(THRESHOLD_DEFAULTS[s]["col"], s, THRESHOLD_DEFAULTS[s]["color"])
               for s in sensors if THRESHOLD_DEFAULTS[s]["col"] in df.columns]

        if len(sel) >= 2:
            fig = go.Figure()
            col_n, col_l, col_c = sel[0]
            fig.add_trace(go.Scatter(x=df_s["timestamp"], y=df_s[col_n], name=col_l,
                line=dict(color=col_c, width=1.5), connectgaps=False, yaxis="y1"))
            for col_n, col_l, col_c in sel[1:]:
                fig.add_trace(go.Scatter(x=df_s["timestamp"], y=df_s[col_n], name=col_l,
                    line=dict(color=col_c, width=1.5, dash="dot"), connectgaps=False, yaxis="y2"))
            fig.update_layout(
                title="All sensors overview",
                yaxis=dict(title=sel[0][1], color=sel[0][2], showgrid=True, gridcolor="rgba(0,0,0,0.05)"),
                yaxis2=dict(title=" / ".join([c[1] for c in sel[1:]]), overlaying="y", side="right", showgrid=False),
                legend=dict(x=0.01, y=0.99),
                **{k: v for k, v in CHART.items() if k not in ("xaxis", "yaxis")},
            )
            st.plotly_chart(fig, use_container_width=True)

        # Graphiques individuels avec zones de seuil vert
        def threshold_chart(col, label, color, lo, hi):
            """Graphique d'un capteur avec zone verte (safe) et lignes min/max."""
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=df_s["timestamp"], y=df_s[col], mode="lines",
                name=label, line=dict(color=color, width=1.5), connectgaps=False))
            fig.add_hrect(y0=lo, y1=hi, fillcolor="rgba(34,197,94,0.07)",
                          annotation_text="Safe zone", line_width=0)
            fig.add_hline(y=hi, line_dash="dash", line_color="#ef4444", annotation_text="Max")
            fig.add_hline(y=lo, line_dash="dash", line_color="#3b82f6", annotation_text="Min")
            fig.update_layout(title=f"{label} vs Thresholds", **CHART)
            st.plotly_chart(fig, use_container_width=True)

        for sensor in sensors:
            cfg = THRESHOLD_DEFAULTS[sensor]
            if cfg["col"] in df.columns and sensor in thresholds:
                lo, hi = thresholds[sensor]
                threshold_chart(cfg["col"], f"{sensor} ({cfg['unit']})", cfg["color"], lo, hi)