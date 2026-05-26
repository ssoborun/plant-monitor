import requests
import os
import streamlit as st
from datetime import datetime

API_KEY = os.getenv("OPENWEATHER_API_KEY", "")
BASE_URL = "https://api.openweathermap.org/data/2.5"
DEFAULT_CITY = os.getenv("WEATHER_CITY", "Lausanne")
DEFAULT_COUNTRY = os.getenv("WEATHER_COUNTRY", "CH")

WEATHER_ICONS = {
    "Clear": "☀️",
    "Clouds": "☁️",
    "Rain": "🌧️",
    "Drizzle": "🌦️",
    "Thunderstorm": "⛈️",
    "Snow": "❄️",
    "Mist": "🌫️",
    "Fog": "🌫️",
    "Haze": "🌫️",
}


@st.cache_data(ttl=600)
def get_current_weather(city: str = DEFAULT_CITY, country: str = DEFAULT_COUNTRY) -> dict | None:
    """Get current weather from OpenWeatherMap."""
    if not API_KEY:
        return None
    try:
        url = f"{BASE_URL}/weather"
        params = {
            "q": f"{city},{country}",
            "appid": API_KEY,
            "units": "metric",
            "lang": "en"
        }
        r = requests.get(url, params=params, timeout=5)
        r.raise_for_status()
        data = r.json()
        main = data.get("weather", [{}])[0].get("main", "")
        return {
            "city": data["name"],
            "temp": round(data["main"]["temp"], 1),
            "feels_like": round(data["main"]["feels_like"], 1),
            "humidity": data["main"]["humidity"],
            "pressure": data["main"]["pressure"],
            "description": data["weather"][0]["description"].capitalize(),
            "main": main,
            "icon": WEATHER_ICONS.get(main, "🌡️"),
            "wind_speed": data["wind"]["speed"],
            "visibility": data.get("visibility", 0) // 1000,
            "sunrise": datetime.fromtimestamp(data["sys"]["sunrise"]).strftime("%H:%M"),
            "sunset": datetime.fromtimestamp(data["sys"]["sunset"]).strftime("%H:%M"),
        }
    except Exception as e:
        return None


@st.cache_data(ttl=3600)
def get_forecast(city: str = DEFAULT_CITY, country: str = DEFAULT_COUNTRY) -> list:
    """Get 5-day weather forecast."""
    if not API_KEY:
        return []
    try:
        url = f"{BASE_URL}/forecast"
        params = {
            "q": f"{city},{country}",
            "appid": API_KEY,
            "units": "metric",
            "cnt": 40,
            "lang": "en"
        }
        r = requests.get(url, params=params, timeout=5)
        r.raise_for_status()
        data = r.json()

        # Group by day, take midday forecast
        days = {}
        for item in data["list"]:
            dt = datetime.fromtimestamp(item["dt"])
            day_key = dt.strftime("%Y-%m-%d")
            hour = dt.hour
            if day_key not in days or abs(hour - 12) < abs(days[day_key]["hour"] - 12):
                main = item["weather"][0]["main"]
                days[day_key] = {
                    "date": dt.strftime("%a %d %b"),
                    "hour": hour,
                    "temp_max": round(item["main"]["temp_max"], 1),
                    "temp_min": round(item["main"]["temp_min"], 1),
                    "description": item["weather"][0]["description"].capitalize(),
                    "main": main,
                    "icon": WEATHER_ICONS.get(main, "🌡️"),
                    "rain_prob": round(item.get("pop", 0) * 100),
                    "humidity": item["main"]["humidity"],
                }
        return list(days.values())[:5]
    except Exception:
        return []


def get_weather_alerts(weather: dict) -> list:
    """Generate smart alerts based on current weather."""
    if not weather:
        return []
    alerts = []
    if weather.get("main") in ["Rain", "Drizzle", "Thunderstorm"]:
        alerts.append({"type": "warning", "msg": "🌧️ Rain expected — you may not need to water today"})
    if weather.get("temp", 20) > 30:
        alerts.append({"type": "danger", "msg": "🌡️ Very hot outside — check indoor humidity"})
    if weather.get("main") == "Thunderstorm":
        alerts.append({"type": "danger", "msg": "⛈️ Storm alert — secure any outdoor equipment"})
    if weather.get("wind_speed", 0) > 10:
        alerts.append({"type": "warning", "msg": f"💨 Strong winds: {weather['wind_speed']} m/s"})
    return alerts