from google.cloud import bigquery
from google.oauth2 import service_account
import pandas as pd
import streamlit as st
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

PROJECT_ID = "cryptic-spanner-311208"
DATASET_ID = os.getenv("BQ_DATASET_ID", "plant_monitoring")
TABLE_ID = os.getenv("BQ_TABLE_ID", "sensor_readings")
FULL_TABLE = f"cryptic-spanner-311208.{DATASET_ID}.{TABLE_ID}"


def get_client():
    try:
        # Streamlit Cloud : utilise st.secrets
        if "gcp_service_account" in st.secrets:
            credentials = service_account.Credentials.from_service_account_info(
                st.secrets["gcp_service_account"],
                scopes=["https://www.googleapis.com/auth/cloud-platform"]
            )
        else:
            # Local : utilise le fichier service_account.json
            import pathlib
            base_dir = pathlib.Path(__file__).parent.parent
            key_path = str(base_dir / "service_account.json")
            credentials = service_account.Credentials.from_service_account_file(
                key_path,
                scopes=["https://www.googleapis.com/auth/cloud-platform"]
            )

        client = bigquery.Client(
            credentials=credentials,
            project="cryptic-spanner-311208",
            location="europe-west6"
        )
        return client
    except Exception as e:
        st.error(f"❌ BigQuery connection failed: {e}")
        return None

def get_latest_reading() -> dict | None:
    """Get the most recent sensor reading."""
    client = get_client()
    if not client:
        return None
    query = f"""
        SELECT *
        FROM `{FULL_TABLE}`
        ORDER BY timestamp DESC
        LIMIT 1
    """
    try:
        df = client.query(query).to_dataframe()
        if df.empty:
            return None
        return df.iloc[0].to_dict()
    except Exception as e:
        st.error(f"Query error: {e}")
        return None


def get_readings(
    start_date: datetime = None,
    end_date: datetime = None,
    limit: int = 5000
) -> pd.DataFrame:
    """Get sensor readings with optional date filter."""
    client = get_client()
    if not client:
        return pd.DataFrame()

    where_clauses = []
    if start_date:
        where_clauses.append(f"timestamp >= '{start_date.isoformat()}'")
    if end_date:
        where_clauses.append(f"timestamp <= '{end_date.isoformat()}'")

    where_str = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""

    query = f"""
        SELECT *
        FROM `{FULL_TABLE}`
        {where_str}
        ORDER BY timestamp DESC
        LIMIT {limit}
    """
    try:
        df = client.query(query).to_dataframe()
        if not df.empty and "timestamp" in df.columns:
            df["timestamp"] = pd.to_datetime(df["timestamp"])
        return df
    except Exception as e:
        st.error(f"Query error: {e}")
        return pd.DataFrame()


def get_stats(start_date: datetime = None, end_date: datetime = None) -> dict:
    """Get aggregated statistics for a period."""
    client = get_client()
    if not client:
        return {}

    where_clauses = []
    if start_date:
        where_clauses.append(f"timestamp >= '{start_date.isoformat()}'")
    if end_date:
        where_clauses.append(f"timestamp <= '{end_date.isoformat()}'")

    where_str = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""

    query = f"""
        SELECT
            COUNT(*) as total_readings,
            ROUND(AVG(temperature), 2) as avg_temp,
            ROUND(MIN(temperature), 2) as min_temp,
            ROUND(MAX(temperature), 2) as max_temp,
            ROUND(AVG(humidity), 2) as avg_humidity,
            ROUND(AVG(pressure), 2) as avg_pressure,
            ROUND(AVG(soil_raw), 0) as avg_soil_raw,
            MIN(timestamp) as first_reading,
            MAX(timestamp) as last_reading
        FROM `{FULL_TABLE}`
        {where_str}
    """
    try:
        df = client.query(query).to_dataframe()
        if df.empty:
            return {}
        return df.iloc[0].to_dict()
    except Exception as e:
        st.error(f"Stats query error: {e}")
        return {}


def get_hourly_averages(days: int = 7) -> pd.DataFrame:
    """Get hourly averages for charts."""
    client = get_client()
    if not client:
        return pd.DataFrame()

    query = f"""
        SELECT
            TIMESTAMP_TRUNC(timestamp, HOUR) as hour,
            ROUND(AVG(temperature), 2) as avg_temperature,
            ROUND(AVG(humidity), 2) as avg_humidity,
            ROUND(AVG(pressure), 2) as avg_pressure,
            ROUND(AVG(soil_raw), 0) as avg_soil_raw,
            COUNT(*) as readings_count
        FROM `{FULL_TABLE}`
        WHERE timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL {days} DAY)
        GROUP BY hour
        ORDER BY hour ASC
    """
    try:
        df = client.query(query).to_dataframe()
        if not df.empty:
            df["hour"] = pd.to_datetime(df["hour"])
        return df
    except Exception as e:
        st.error(f"Hourly averages error: {e}")
        return pd.DataFrame()


def delete_readings(start_date: datetime, end_date: datetime) -> int:
    """Delete readings in a date range. Returns number of rows deleted."""
    client = get_client()
    if not client:
        return 0
    query = f"""
        DELETE FROM `{FULL_TABLE}`
        WHERE timestamp >= '{start_date.isoformat()}'
        AND timestamp <= '{end_date.isoformat()}'
    """
    try:
        job = client.query(query)
        job.result()
        return job.num_dml_affected_rows or 0
    except Exception as e:
        st.error(f"Delete error: {e}")
        return 0