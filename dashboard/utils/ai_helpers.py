import os
import json
import pandas as pd
import streamlit as st
import anthropic
from dotenv import load_dotenv

load_dotenv()

try:
    ANTHROPIC_API_KEY = st.secrets["ANTHROPIC_API_KEY"]
except Exception:
    ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")


def get_claude_client():
    return anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)


def get_tts_client():
    try:
        from google.cloud import texttospeech
        from google.oauth2 import service_account
        try:
            credentials = service_account.Credentials.from_service_account_info(
                dict(st.secrets["gcp_service_account"]),
                scopes=["https://www.googleapis.com/auth/cloud-platform"]
            )
        except Exception:
            import pathlib
            key_path = str(pathlib.Path(__file__).parent.parent / "service_account.json")
            credentials = service_account.Credentials.from_service_account_file(
                key_path, scopes=["https://www.googleapis.com/auth/cloud-platform"]
            )
        return texttospeech.TextToSpeechClient(credentials=credentials)
    except Exception:
        return None


def analyze_data_with_ai(df: pd.DataFrame, user_question: str) -> str:
    if df.empty:
        return "No data available for the selected period."

    client = get_claude_client()
    sample_df = df.head(200).copy()
    if "timestamp" in sample_df.columns:
        sample_df["timestamp"] = sample_df["timestamp"].astype(str)

    summary = {
        "total_readings": len(df),
        "period": f"{df['timestamp'].min()} to {df['timestamp'].max()}" if "timestamp" in df.columns else "unknown",
        "temperature": {"avg": round(df["temperature"].mean(), 2), "min": round(df["temperature"].min(), 2), "max": round(df["temperature"].max(), 2)} if "temperature" in df.columns else None,
        "humidity": {"avg": round(df["humidity"].mean(), 2), "min": round(df["humidity"].min(), 2), "max": round(df["humidity"].max(), 2)} if "humidity" in df.columns else None,
        "soil_raw": {"avg": round(df["soil_raw"].mean(), 0), "min": round(df["soil_raw"].min(), 0), "max": round(df["soil_raw"].max(), 0)} if "soil_raw" in df.columns else None,
        "pressure": {"avg": round(df["pressure"].mean(), 2), "min": round(df["pressure"].min(), 2), "max": round(df["pressure"].max(), 2)} if "pressure" in df.columns else None,
    }

    prompt = f"""You are an IoT data analyst for a plant monitoring system using an M5Stack sensor.

Statistical summary:
{json.dumps(summary, indent=2, default=str)}

Raw sensor data (first {len(sample_df)} rows, CSV):
{sample_df.to_csv(index=False)}

Question: {user_question}

Answer clearly and concisely using specific numbers from the data."""

    try:
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=500,
            messages=[{"role": "user", "content": prompt}]
        )
        return response.content[0].text
    except Exception as e:
        return f"AI Error: {e}"


def text_to_speech(text: str) -> bytes | None:
    try:
        from google.cloud import texttospeech
        client = get_tts_client()
        if not client:
            return None
        response = client.synthesize_speech(
            input=texttospeech.SynthesisInput(text=text),
            voice=texttospeech.VoiceSelectionParams(
                language_code="en-US",
                name="en-US-Neural2-F",
                ssml_gender=texttospeech.SsmlVoiceGender.FEMALE
            ),
            audio_config=texttospeech.AudioConfig(
                audio_encoding=texttospeech.AudioEncoding.MP3
            )
        )
        return response.audio_content
    except Exception:
        return None


def speech_to_text(audio_bytes: bytes) -> str | None:
    try:
        from google.cloud import speech
        from google.oauth2 import service_account
        try:
            credentials = service_account.Credentials.from_service_account_info(
                dict(st.secrets["gcp_service_account"]),
                scopes=["https://www.googleapis.com/auth/cloud-platform"]
            )
        except Exception:
            import pathlib
            key_path = str(pathlib.Path(__file__).parent.parent / "service_account.json")
            credentials = service_account.Credentials.from_service_account_file(
                key_path, scopes=["https://www.googleapis.com/auth/cloud-platform"]
            )
        client = speech.SpeechClient(credentials=credentials)
        response = client.recognize(
            config=speech.RecognitionConfig(
                encoding=speech.RecognitionConfig.AudioEncoding.MP3,
                language_code="en-US"
            ),
            audio=speech.RecognitionAudio(content=audio_bytes)
        )
        return response.results[0].alternatives[0].transcript if response.results else None
    except Exception:
        return None


def generate_sensor_summary(latest: dict, weather: dict = None) -> str:
    parts = []
    if latest:
        temp = latest.get("temperature")
        hum = latest.get("humidity")
        soil = latest.get("soil_raw")
        if temp:
            parts.append(f"Indoor temperature is {temp:.1f}°C")
        if hum:
            status = "comfortable" if 40 <= hum <= 60 else ("low" if hum < 40 else "high")
            parts.append(f"humidity is {hum:.1f}% which is {status}")
        if soil:
            parts.append(f"soil moisture reading is {soil}")
    if weather:
        parts.append(f"Outside it is {weather.get('temp')}°C with {weather.get('description', '').lower()}")
    return (". ".join(parts) + ".") if parts else "No data available at the moment."