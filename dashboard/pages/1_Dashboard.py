import streamlit as st
import plotly.graph_objects as go
import pandas as pd
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.bigquery_client import get_latest_reading, get_hourly_averages, get_stats, get_readings
from utils.weather import get_current_weather, get_forecast, get_weather_alerts

st.set_page_config(page_title="Plant Monitor — Dashboard", page_icon="🌱", layout="wide")

# ── Décalage horaire Suisse (UTC+2 en été) ────────────────────────────────────
SWISS_OFFSET = pd.Timedelta(hours=2)

# ── CSS global — styles des cartes, métriques, alertes, météo ─────────────────
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
    transition: transform 0.15s ease, box-shadow 0.15s ease; cursor: pointer;
}
div[data-testid="stMetric"]:hover { transform: translateY(-1px); box-shadow: 0 4px 16px rgba(0,0,0,0.1); border-color: rgba(37,99,235,0.3); }
div[data-testid="stMetric"] label, div[data-testid="stMetric"] [data-testid="stMetricLabel"] p { font-size: 0.68rem !important; font-weight: 700 !important; text-transform: uppercase; letter-spacing: 0.12em; opacity: 0.5; }
div[data-testid="stMetric"] [data-testid="stMetricValue"] { font-size: 1.65rem !important; font-weight: 600 !important; font-family: 'JetBrains Mono', monospace !important; letter-spacing: -0.02em; }
div[data-testid="stMetric"] [data-testid="stMetricDelta"] { font-size: 0.75rem !important; }
.section-title { font-size: 0.65rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.2em; margin-bottom: 14px; padding-bottom: 8px; border-bottom: 1px solid rgba(128,128,128,0.12); color: #2563eb; }
.detail-panel { border-radius: 14px; padding: 20px; border: 1px solid rgba(37,99,235,0.2); background: rgba(37,99,235,0.02); margin: 12px 0; }
.stat-box { border-radius: 10px; padding: 12px 16px; border: 1px solid rgba(128,128,128,0.12); text-align: center; }
.stat-label { font-size: 0.65rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.1em; opacity: 0.45; margin-bottom: 4px; }
.stat-value { font-size: 1.3rem; font-weight: 600; font-family: 'JetBrains Mono', monospace; }
.weather-card { border-radius: 10px; padding: 12px 10px; border: 1px solid rgba(128,128,128,0.12); text-align: center; box-shadow: 0 1px 4px rgba(0,0,0,0.04); }
.forecast-day  { font-weight: 700; font-size: 0.68rem; text-transform: uppercase; letter-spacing: 0.08em; color: #2563eb; }
.forecast-icon { font-size: 1.5rem; margin: 6px 0; }
.forecast-temp { font-size: 0.82rem; font-family: 'JetBrains Mono', monospace; font-weight: 500; }
.forecast-rain { font-size: 0.68rem; margin-top: 3px; color: #3b82f6; }
.forecast-desc { font-size: 0.65rem; opacity: 0.4; margin-top: 2px; }
.alert-box { padding: 10px 14px; border-radius: 8px; margin: 5px 0; font-size: 0.85rem; font-weight: 500; }
.alert-warning { background: rgba(245,158,11,0.08); border: 1px solid rgba(245,158,11,0.25); color: #92400e; }
.alert-danger  { background: rgba(239,68,68,0.08);  border: 1px solid rgba(239,68,68,0.25);  color: #991b1b; }
.alert-success { background: rgba(34,197,94,0.08);  border: 1px solid rgba(34,197,94,0.2);   color: #166534; }
hr { border-color: rgba(128,128,128,0.1) !important; margin: 20px 0 !important; }
</style>
""", unsafe_allow_html=True)

# ── Initialisation de l'état de session ───────────────────────────────────────
# Stocke quel capteur est actuellement sélectionné (pour afficher le panneau détail)
if "selected_sensor" not in st.session_state:
    st.session_state["selected_sensor"] = None

# ── En-tête : titre + bouton refresh + heure dernière lecture ─────────────────
col_title, col_refresh, col_time = st.columns([3, 1, 2])
with col_title:
    st.markdown("## 🌱 Plant Monitor")
with col_refresh:
    # Vide le cache et recharge toutes les données
    if st.button("↻ Refresh"):
        st.cache_data.clear()
        st.rerun()

# ── Chargement des données ────────────────────────────────────────────────────
latest    = get_latest_reading()                          # dernière lecture capteurs
weather   = get_current_weather()                         # météo Lausanne (OpenWeatherMap)
hourly_df = get_hourly_averages(days=7)                   # moyennes horaires sur 7 jours
stats_24h = get_stats(start_date=pd.Timestamp.now(tz="UTC") - pd.Timedelta(hours=24))  # stats dernières 24h

with col_time:
    if latest and latest.get("timestamp"):
        ts = pd.Timestamp(latest["timestamp"]) + SWISS_OFFSET
        st.caption(f"Last update — {ts.strftime('%d %b %Y, %H:%M:%S')}")

st.markdown("---")


# ── Panneau détail d'un capteur ───────────────────────────────────────────────
def show_detail_panel(sensor_key, label, unit, color, df_col):
    """Affiche un panneau avec stats et graphique 24h pour un capteur cliqué."""
    st.markdown('<div class="detail-panel">', unsafe_allow_html=True)

    col_title, col_close = st.columns([5, 1])
    with col_title:
        st.markdown(f"**{label} — Detail View**")
    with col_close:
        # Ferme le panneau en réinitialisant la session
        if st.button("✕ Close", key=f"close_{sensor_key}"):
            st.session_state["selected_sensor"] = None
            st.rerun()

    # Récupère les données des 24 dernières heures
    df_24h = get_readings(start_date=pd.Timestamp.now(tz="UTC") - pd.Timedelta(hours=24), limit=500)

    if not df_24h.empty and df_col in df_24h.columns:
        df_24h["timestamp"] = df_24h["timestamp"] + SWISS_OFFSET
        series = pd.to_numeric(df_24h[df_col], errors="coerce").dropna()

        # Fonction locale pour formater les valeurs numériques
        fmt = lambda v: f"{float(v):.1f}" if v is not None else "—"

        # Affiche 4 stats : valeur actuelle, moyenne, min, max
        current = series.iloc[0] if not series.empty else None
        for col_st, lbl, val in zip(
            st.columns(4),
            ["Current", "Average", "Min", "Max"],
            [current, series.mean(), series.min(), series.max()]
        ):
            c_style = f'style="color:{color}"' if lbl == "Current" else ""
            with col_st:
                st.markdown(
                    f'<div class="stat-box"><div class="stat-label">{lbl}</div>'
                    f'<div class="stat-value" {c_style}>{fmt(val)} {unit}</div></div>',
                    unsafe_allow_html=True
                )

        st.markdown("<br>", unsafe_allow_html=True)

        # Graphique ligne 24h
        df_sorted = df_24h.sort_values("timestamp")
        fig = go.Figure(go.Scatter(
            x=df_sorted["timestamp"], y=pd.to_numeric(df_sorted[df_col], errors="coerce"),
            mode="lines", line=dict(color=color, width=2),
            fill="tozeroy", fillcolor="rgba(128,128,128,0.08)",
            connectgaps=False, showlegend=False
        ))
        fig.update_layout(
            template="plotly_white", paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)", height=200,
            margin=dict(l=40, r=20, t=10, b=36),
            font=dict(family="Inter, sans-serif", size=11),
            xaxis=dict(showgrid=True, gridcolor="rgba(0,0,0,0.05)", title="Last 24 hours"),
            yaxis=dict(showgrid=True, gridcolor="rgba(0,0,0,0.05)", title=unit, autorange=True),
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No data available for the last 24 hours.")

    st.markdown('</div>', unsafe_allow_html=True)


# ── Cartes capteurs (cliquables) ──────────────────────────────────────────────
st.markdown('<div class="section-title">Last 10 Sensors Readings</div>', unsafe_allow_html=True)

# Liste des capteurs : (clé, titre, unité, couleur, colonne BigQuery)
SENSORS = [
    ("temperature", "Temperature",   "°C",  "#f97316", "temperature"),
    ("humidity",    "Humidity",      "%",   "#3b82f6", "humidity"),
    ("pressure",    "Pressure",      "hPa", "#a855f7", "pressure"),
    ("soil_raw",    "Soil Raw",      "ADC", "#22c55e", "soil_raw"),
    ("soil_moist",  "Soil Moist.",   "%",   "#06b6d4", "soil_moisture"),
]

if latest:
    temp       = latest.get("temperature")
    hum        = latest.get("humidity")
    pres       = latest.get("pressure")
    soil_raw   = latest.get("soil_raw")
    soil_moist = latest.get("soil_moisture")

    # Calcul des deltas affichés sous chaque valeur
    deltas = {
        "temperature": f"{round(temp - stats_24h['avg_temp'], 1):+.1f}°C vs 24h" if stats_24h.get('avg_temp') and temp else "—",
        "humidity":    "Optimal" if hum and 40 <= hum <= 60 else ("Too dry" if hum and hum < 40 else "Too humid"),
        "pressure":    "High" if pres and pres > 1013 else ("Low" if pres and pres < 1000 else "Normal"),
        "soil_raw":    "Wet" if soil_raw and soil_raw < 1500 else ("Moist" if soil_raw and soil_raw < 2000 else "Dry"),
        "soil_moist":  "Calibrated",
    }

    # Valeurs formatées pour l'affichage
    values = {
        "temperature": f"{temp:.1f} °C" if temp else "—",
        "humidity":    f"{hum:.1f} %" if hum else "—",
        "pressure":    f"{pres:.1f} hPa" if pres else "—",
        "soil_raw":    f"{soil_raw}" if soil_raw else "—",
        "soil_moist":  f"{soil_moist} %" if soil_moist else "—",
    }

    # Affichage des 5 cartes en colonnes
    for col_st, (key, title, _, color, __) in zip(st.columns(5), SENSORS):
        with col_st:
            # Carte HTML custom (plus de contrôle visuel qu'un st.metric)
            st.markdown(f"""
            <div style="border-radius:12px; padding:18px 16px; border:1px solid rgba(128,128,128,0.15);
                        box-shadow:0 1px 8px rgba(0,0,0,0.05); min-height:110px;
                        display:flex; flex-direction:column; justify-content:space-between;">
                <div style="font-size:0.68rem; font-weight:700; text-transform:uppercase;
                            letter-spacing:0.12em; opacity:0.5; margin-bottom:6px;">{title}</div>
                <div style="font-size:1.65rem; font-weight:600; font-family:'JetBrains Mono',monospace;
                            letter-spacing:-0.02em; margin-bottom:6px;">{values[key]}</div>
                <div style="font-size:0.75rem; color:#16a34a;">↑ {deltas[key]}</div>
            </div>
            """, unsafe_allow_html=True)
            # Bouton qui ouvre/ferme le panneau détail de ce capteur
            if st.button("Details", key=f"btn_{key}", use_container_width=True):
                st.session_state["selected_sensor"] = None if st.session_state["selected_sensor"] == key else key
                st.rerun()

    # Affiche le panneau détail si un capteur est sélectionné
    if st.session_state["selected_sensor"]:
        key = st.session_state["selected_sensor"]
        match = {s[0]: s for s in SENSORS}
        if key in match:
            _, label, unit, color, df_col = match[key]
            show_detail_panel(key, label, unit, color, df_col)
else:
    st.warning("No sensor data available.")


# ── Tableau des 10 dernières lectures ─────────────────────────────────────────
recent_df = get_readings(limit=11)
if not recent_df.empty:
    disp = recent_df.copy()
    if "timestamp" in disp.columns:
        disp["timestamp"] = (disp["timestamp"] + SWISS_OFFSET).dt.strftime("%Y-%m-%d %H:%M:%S")
    # Tri décroissant, on enlève la 1ère ligne (déjà affichée dans les cartes)
    disp = disp.sort_values("timestamp", ascending=False).reset_index(drop=True).iloc[1:]
    cols_order = [c for c in ["timestamp","temperature","humidity","pressure","soil_raw","soil_moisture"] if c in disp.columns]
    st.dataframe(disp[cols_order].reset_index(drop=True), use_container_width=True, height=210, hide_index=True)
    st.caption("Last 10 readings — Swiss time (UTC+2)")
else:
    st.info("No recent readings available.")

st.markdown("---")


# ── Météo extérieure Lausanne ─────────────────────────────────────────────────
st.markdown('<div class="section-title">Outdoor Weather — Lausanne</div>', unsafe_allow_html=True)

if weather:
    # 5 métriques météo sur une ligne
    w1, w2, w3, w4, w5 = st.columns(5)
    with w1: st.metric(f"{weather['icon']} {weather['city']}", f"{weather['temp']} °C", delta=f"Feels {weather['feels_like']}°C")
    with w2: st.metric("Condition", weather["description"].capitalize())
    with w3: st.metric("Humidity", f"{weather['humidity']} %")
    with w4: st.metric("Wind", f"{weather['wind_speed']} m/s")
    with w5: st.metric("Sunrise / Sunset", f"{weather['sunrise']} / {weather['sunset']}")

    # Alertes météo (ex: vent fort, pluie)
    for alert in get_weather_alerts(weather):
        st.markdown(f'<div class="alert-box alert-{alert["type"]}">{alert["msg"]}</div>', unsafe_allow_html=True)

    # Prévisions 5 jours
    st.markdown("<br>**5-Day Forecast**", unsafe_allow_html=True)
    forecast = get_forecast()
    if forecast:
        for col_st, day in zip(st.columns(len(forecast)), forecast):
            with col_st:
                st.markdown(f"""<div class="weather-card">
                    <div class="forecast-day">{day['date']}</div>
                    <div class="forecast-icon">{day['icon']}</div>
                    <div class="forecast-temp">{day['temp_max']}° / {day['temp_min']}°</div>
                    <div class="forecast-rain">{day['rain_prob']}% rain</div>
                    <div class="forecast-desc">{day['description']}</div>
                </div>""", unsafe_allow_html=True)
else:
    st.info("Weather data unavailable.")

st.markdown("---")


# ── Alertes seuils ────────────────────────────────────────────────────────────
st.markdown('<div class="section-title">Alerts</div>', unsafe_allow_html=True)

has_alert = False
if latest:
    hum  = latest.get("humidity")
    temp = latest.get("temperature")
    # Vérification des seuils et affichage des alertes correspondantes
    alerts = [
        (hum  and hum < 40,   "warning", "⚠ Humidity below 40% — consider using a humidifier"),
        (hum  and hum > 70,   "warning", "⚠ Humidity above 70% — check for condensation or mold risk"),
        (temp and temp > 28,  "danger",  f"High indoor temperature: {temp:.1f}°C"),
        (temp and temp < 15,  "warning", f"Low indoor temperature: {temp:.1f}°C"),
    ]
    for condition, level, msg in alerts:
        if condition:
            st.markdown(f'<div class="alert-box alert-{level}">{msg}</div>', unsafe_allow_html=True)
            has_alert = True

if not has_alert:
    st.markdown('<div class="alert-box alert-success">✓ All conditions normal</div>', unsafe_allow_html=True)

st.markdown("---")


# ── Graphiques historiques 7 jours ────────────────────────────────────────────
st.markdown('<div class="section-title">Historical Data — Last 7 Days</div>', unsafe_allow_html=True)

# Config commune à tous les graphiques (évite la répétition)
CHART_LAYOUT = dict(
    template="plotly_white", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
    margin=dict(l=50, r=20, t=36, b=36), height=260,
    font=dict(family="Inter, sans-serif", size=11),
    xaxis=dict(showgrid=True, gridcolor="rgba(0,0,0,0.05)", showline=False, zeroline=False),
    yaxis=dict(showgrid=True, gridcolor="rgba(0,0,0,0.05)", showline=False, zeroline=False, autorange=True),
    title_font=dict(size=12, family="Inter, sans-serif"),
)

if not hourly_df.empty:
    # Crée une grille horaire complète pour éviter les trous dans les graphiques
    full_range = pd.date_range(start=hourly_df["hour"].min(), end=hourly_df["hour"].max(), freq="h")
    full_range = full_range.tz_localize(None)
    hourly_df["hour"] = pd.to_datetime(hourly_df["hour"]).dt.tz_localize(None)
    hdf = pd.DataFrame({"hour": full_range}).merge(hourly_df, on="hour", how="left")
    # Liste des graphiques à afficher : (colonne BQ, titre, unité, couleur)
    charts = [
        ("avg_temperature", "Temperature (°C)", "°C",  "#f97316"),
        ("avg_humidity",    "Humidity (%)",     "%",   "#3b82f6"),
        ("avg_soil_raw",    "Soil Raw ADC",     "ADC", "#22c55e"),
        ("avg_pressure",    "Pressure (hPa)",   "hPa", "#a855f7"),
    ]

    for col, title, unit, color in charts:
        if hdf[col].dropna().empty:
            continue
        fig = go.Figure(go.Scatter(
            x=hdf["hour"], y=hdf[col], mode="lines",
            line=dict(color=color, width=2), connectgaps=False, showlegend=False
        ))
        # Zone verte pour la plage d'humidité optimale (40-60%)
        if col == "avg_humidity":
            fig.add_hrect(y0=40, y1=60, fillcolor="rgba(34,197,94,0.07)",
                          annotation_text="Optimal", annotation_position="top left",
                          annotation_font_size=10, line_width=0)
        fig.update_layout(title=title, yaxis_title=unit, xaxis_title="", **CHART_LAYOUT)
        st.plotly_chart(fig, use_container_width=True)
else:
    st.info("No historical data available yet.")