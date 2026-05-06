import os
from datetime import datetime, timedelta, timezone

import pandas as pd
from google.cloud import bigquery


PROJECT_ID = os.getenv("PROJECT_ID", "")
DATASET_ID = os.getenv("DATASET_ID", "weather_analytics")
INDOOR_TABLE = os.getenv("INDOOR_TABLE", "indoor_metrics")
OUTDOOR_TABLE = os.getenv("OUTDOOR_TABLE", "outdoor_weather")
EVENTS_TABLE = os.getenv("EVENTS_TABLE", "device_events")


def _client() -> bigquery.Client:
    return bigquery.Client(project=PROJECT_ID or None)


def latest_indoor(device_id: str) -> pd.DataFrame:
    query = f"""
    SELECT event_ts, device_id, temperature_c, humidity_pct, tvoc_ppb, eco2_ppm, motion_detected
    FROM `{PROJECT_ID}.{DATASET_ID}.{INDOOR_TABLE}`
    WHERE device_id = @device_id
    ORDER BY event_ts DESC
    LIMIT 1
    """
    job_config = bigquery.QueryJobConfig(
        query_parameters=[bigquery.ScalarQueryParameter("device_id", "STRING", device_id)]
    )
    return _client().query(query, job_config=job_config).to_dataframe()


def latest_outdoor() -> pd.DataFrame:
    query = f"""
    SELECT weather_ts, temperature_c, humidity_pct, weather_main, weather_description, weather_icon
    FROM `{PROJECT_ID}.{DATASET_ID}.{OUTDOOR_TABLE}`
    ORDER BY weather_ts DESC
    LIMIT 1
    """
    return _client().query(query).to_dataframe()


def indoor_history(device_id: str, days: int) -> pd.DataFrame:
    start_ts = datetime.now(timezone.utc) - timedelta(days=days)
    query = f"""
    SELECT event_ts, temperature_c, humidity_pct, tvoc_ppb, eco2_ppm, motion_detected
    FROM `{PROJECT_ID}.{DATASET_ID}.{INDOOR_TABLE}`
    WHERE device_id = @device_id AND event_ts >= @start_ts
    ORDER BY event_ts ASC
    """
    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("device_id", "STRING", device_id),
            bigquery.ScalarQueryParameter("start_ts", "TIMESTAMP", start_ts),
        ]
    )
    return _client().query(query, job_config=job_config).to_dataframe()


def recent_events(device_id: str, limit: int = 50) -> pd.DataFrame:
    query = f"""
    SELECT event_ts, event_type, severity, message
    FROM `{PROJECT_ID}.{DATASET_ID}.{EVENTS_TABLE}`
    WHERE device_id = @device_id
    ORDER BY event_ts DESC
    LIMIT @limit
    """
    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("device_id", "STRING", device_id),
            bigquery.ScalarQueryParameter("limit", "INT64", limit),
        ]
    )
    return _client().query(query, job_config=job_config).to_dataframe()
