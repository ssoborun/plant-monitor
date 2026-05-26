# Plant & Environment Monitor

> IoT Experimentation Platform — M5Stack Core2 + Google BigQuery + Streamlit

[![Python](https://img.shields.io/badge/Python-3.14-blue)](https://python.org)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.35-red)](https://streamlit.io)
[![BigQuery](https://img.shields.io/badge/Google-BigQuery-blue)](https://cloud.google.com/bigquery)

---

## Project Overview

This project is an IoT experimentation platform for plant and environmental monitoring. Instead of providing a fixed prediction algorithm, it gives users the tools to **collect, explore, visualize, and analyze** their own sensor data.

The system collects data from an **M5Stack Core2** device equipped with sensors, stores it in **Google BigQuery**, and displays it in a **Streamlit dashboard** accessible from anywhere.

**Live Dashboard:** https://plant-monitor-dashboard-m4ftnxeceifzqtdgjdydwv.streamlit.app

---

## Architecture

```
M5Stack Core2 (sensors)
        │
        ▼
Google BigQuery (cloud storage)
        │
        ▼
Streamlit Dashboard (web interface)
        │
        ├── Live sensor readings
        ├── Outdoor weather (OpenWeatherMap)
        ├── Data Explorer (filter, export)
        ├── AI Assistant (Claude + Google TTS/STT)
        └── Alerts & Thresholds
```

The project follows a 3-tier architecture:
- **Data layer**: Google BigQuery stores all sensor readings
- **Middleware/Services**: `utils/` modules handle data retrieval, weather API, and AI
- **UI layer**: Streamlit dashboard (`pages/`) and M5Stack on-device interface

---

## Hardware

- **M5Stack Core2** — main IoT device
- **ENV III Sensor** — temperature, humidity, pressure
- **Air Quality Sensor** — indoor air quality monitoring
- **Motion Sensor** — presence detection for automatic announcements
- **Capacitive Soil Moisture Sensor** (RoboDyn) — raw ADC soil readings

---

## Dashboard Pages

| Page | Description |
|------|-------------|
| Home | Platform overview |
| Dashboard | Live sensor data + outdoor weather + 7-day charts + clickable sensor detail panels |
| Data Explorer | Filter by date/hour, sort, visualize, export CSV/Excel |
| AI Assistant | Ask questions about your data using Claude AI with Google TTS voice output |
| Alerts | Configurable thresholds per sensor, violation history with charts |

---

## Getting Started

### 1. Clone the repository
```bash
git clone https://github.com/ssoborun/plant-monitor-dashboard.git
cd plant-monitor-dashboard/dashboard
```

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

### 3. Configure environment variables
```bash
cp .env.example .env
# Fill in your API keys in .env
```

### 4. Add your Google Cloud service account
- Download your service account JSON from Google Cloud Console
- Rename it to `service_account.json`
- Place it in the project root
- **Never commit this file** — it is excluded by `.gitignore`

### 5. Configure Streamlit secrets (local)
```bash
mkdir .streamlit
cp .streamlit/secrets.toml.example .streamlit/secrets.toml
# Fill in your secrets
```

### 6. Run the dashboard
```bash
streamlit run app.py
```

---

## Required API Keys

| Service | Purpose | Link |
|---------|---------|------|
| Google Cloud Service Account | BigQuery + TTS + STT | [console.cloud.google.com](https://console.cloud.google.com) |
| OpenWeatherMap | Outdoor weather data | [openweathermap.org](https://openweathermap.org) |
| Anthropic Claude | AI data analysis | [console.anthropic.com](https://console.anthropic.com) |

---

## BigQuery Schema

**Dataset:** `plant_monitoring`  
**Table:** `sensor_readings`

| Column | Type | Description |
|--------|------|-------------|
| timestamp | TIMESTAMP | Reading time (UTC) |
| device_id | STRING | M5Stack device ID |
| temperature | FLOAT | °C (ENV III sensor) |
| humidity | FLOAT | % (ENV III sensor) |
| pressure | FLOAT | hPa (ENV III sensor) |
| soil_raw | INTEGER | Raw ADC value |
| soil_moisture | STRING | Calibrated moisture % |

---

## Project Structure

```
dashboard/
├── app.py                      # Main entry point
├── pages/
│   ├── 1_Dashboard.py          # Live data + weather + charts
│   ├── 2_Data_Explorer.py      # Filter, sort, export
│   ├── 3_AI_Assistant.py       # Claude AI chat + Google TTS
│   └── 4_Alerts.py             # Threshold monitoring
├── utils/
│   ├── bigquery_client.py      # BigQuery queries
│   ├── weather.py              # OpenWeatherMap API
│   └── ai_helpers.py           # Claude AI + Google TTS/STT
├── .env.example                # Environment variables template
├── .gitignore                  # Excludes secrets and credentials
└── requirements.txt            # Python dependencies
```

---

## Environment Variables

Create a `.env` file based on `.env.example`:

```
GCP_PROJECT_ID=your-project-id
BQ_DATASET_ID=plant_monitoring
BQ_TABLE_ID=sensor_readings
OPENWEATHER_API_KEY=your-key
WEATHER_CITY=Lausanne
WEATHER_COUNTRY=CH
ANTHROPIC_API_KEY=your-key
GOOGLE_APPLICATION_CREDENTIALS=service_account.json
```

---

## Deployment on Streamlit Cloud

1. Push code to GitHub (without secrets)
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. Connect your GitHub repository
4. Add all secrets in Streamlit Cloud → Settings → Secrets

---

## Team

| Name | Role |
|------|------|
| Satchyn Soborun | Streamlit dashboard, AI integration, Google TTS/STT, Cloud setup, BigQuery |
| Manuel | M5Stack firmware, sensor integration, data collection, motion/air quality sensors |

---

## Demo Video

[Link to YouTube demo — coming soon]

---

## License

Academic project — UNIL 2026
