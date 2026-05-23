from datetime import datetime, timezone
from typing import Any, Dict

from google.cloud import bigquery

from config import settings
from models import IngestRequest


class BigQueryRepository:
    def __init__(self) -> None:
        client_project = settings.project_id or None
        self.client = bigquery.Client(project=client_project)

    def _table(self, table_name: str) -> str:
        return f"{settings.project_id}.{settings.dataset_id}.{table_name}"

    def insert_indoor_reading(self, payload: IngestRequest) -> Dict[str, bool]:
        row = {
            "event_ts": payload.timestamp.isoformat(),
            "device_id": payload.device_id,
            "temperature_c": payload.indoor.temperature_c,
            "humidity_pct": payload.indoor.humidity_pct,
            "tvoc_ppb": payload.indoor.tvoc_ppb,
            "eco2_ppm": payload.indoor.eco2_ppm,
            "motion_detected": payload.motion.detected,
            "pir_sensor_id": payload.motion.pir_sensor_id,
            "firmware_version": payload.meta.firmware_version,
            "wifi_ssid": payload.meta.wifi_ssid,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        errors = self.client.insert_rows_json(self._table(settings.indoor_table), [row])
        if errors:
            raise RuntimeError(f"BigQuery insert failed: {errors}")
        return self._compute_alerts(payload)

    def insert_outdoor_weather(self, weather_row: Dict[str, Any]) -> None:
        errors = self.client.insert_rows_json(self._table(settings.outdoor_table), [weather_row])
        if errors:
            raise RuntimeError(f"BigQuery outdoor insert failed: {errors}")

    def insert_event(
        self,
        device_id: str,
        event_type: str,
        severity: str,
        message: str,
        payload_json: str = "{}",
    ) -> None:
        row = {
            "event_ts": datetime.now(timezone.utc).isoformat(),
            "device_id": device_id,
            "event_type": event_type,
            "severity": severity,
            "message": message,
            "payload_json": payload_json,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        errors = self.client.insert_rows_json(self._table(settings.events_table), [row])
        if errors:
            raise RuntimeError(f"BigQuery event insert failed: {errors}")

    def upsert_latest_state(self, device_id: str) -> None:
        query = f"""
        MERGE `{self._table(settings.latest_table)}` T
        USING (
          SELECT
            @device_id AS device_id,
            CURRENT_TIMESTAMP() AS updated_at,
            (
              SELECT TO_JSON_STRING(STRUCT(
                event_ts,
                temperature_c,
                humidity_pct,
                tvoc_ppb,
                eco2_ppm,
                motion_detected
              ))
              FROM `{self._table(settings.indoor_table)}`
              WHERE device_id = @device_id
              ORDER BY event_ts DESC
              LIMIT 1
            ) AS indoor_json,
            (
              SELECT TO_JSON_STRING(STRUCT(
                weather_ts,
                temperature_c,
                humidity_pct,
                weather_main,
                weather_description,
                weather_icon
              ))
              FROM `{self._table(settings.outdoor_table)}`
              ORDER BY weather_ts DESC
              LIMIT 1
            ) AS outdoor_json,
            TO_JSON_STRING(STRUCT('ok' AS status)) AS status_json
        ) S
        ON T.device_id = S.device_id
        WHEN MATCHED THEN UPDATE SET
          updated_at = S.updated_at,
          indoor_json = S.indoor_json,
          outdoor_json = S.outdoor_json,
          status_json = S.status_json
        WHEN NOT MATCHED THEN
          INSERT (device_id, updated_at, indoor_json, outdoor_json, status_json)
          VALUES (S.device_id, S.updated_at, S.indoor_json, S.outdoor_json, S.status_json)
        """
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("device_id", "STRING", device_id),
            ]
        )
        self.client.query(query, job_config=job_config).result()

    def get_latest_snapshot(self, device_id: str) -> Dict[str, Any]:
        query = f"""
        SELECT indoor_json, outdoor_json, updated_at
        FROM `{self._table(settings.latest_table)}`
        WHERE device_id = @device_id
        ORDER BY updated_at DESC
        LIMIT 1
        """
        job_config = bigquery.QueryJobConfig(
            query_parameters=[bigquery.ScalarQueryParameter("device_id", "STRING", device_id)]
        )
        rows = list(self.client.query(query, job_config=job_config).result())
        if not rows:
            return {"indoor": {}, "outdoor": {}, "updated_at": datetime.now(timezone.utc).isoformat()}
        row = rows[0]
        return {
            "indoor": row.indoor_json or "{}",
            "outdoor": row.outdoor_json or "{}",
            "updated_at": row.updated_at.isoformat() if row.updated_at else datetime.now(timezone.utc).isoformat(),
        }

    def get_latest_outdoor(self) -> Dict[str, Any]:
        query = f"""
        SELECT weather_ts, temperature_c, humidity_pct, weather_main, weather_description, weather_icon
        FROM `{self._table(settings.outdoor_table)}`
        ORDER BY weather_ts DESC
        LIMIT 1
        """
        rows = list(self.client.query(query).result())
        if not rows:
            return {}
        row = rows[0]
        return {
            "weather_ts": row.weather_ts.isoformat() if row.weather_ts else None,
            "temperature_c": row.temperature_c,
            "humidity_pct": row.humidity_pct,
            "weather_main": row.weather_main,
            "weather_description": row.weather_description,
            "weather_icon": row.weather_icon,
        }

    def get_day_summary(self, device_id: str, days_ago: int) -> Dict[str, Any]:
        query = f"""
        SELECT
          DATE(event_ts) AS d,
          AVG(temperature_c) AS avg_temp_c,
          MIN(temperature_c) AS min_temp_c,
          MAX(temperature_c) AS max_temp_c,
          AVG(humidity_pct) AS avg_humidity_pct,
          MAX(humidity_pct) AS max_humidity_pct
        FROM `{self._table(settings.indoor_table)}`
        WHERE device_id = @device_id
          AND DATE(event_ts) = DATE_SUB(CURRENT_DATE(), INTERVAL @days_ago DAY)
        GROUP BY d
        LIMIT 1
        """
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("device_id", "STRING", device_id),
                bigquery.ScalarQueryParameter("days_ago", "INT64", int(days_ago)),
            ]
        )
        rows = list(self.client.query(query, job_config=job_config).result())
        if not rows:
            return {}
        row = rows[0]
        return {
            "date": row.d.isoformat() if row.d else None,
            "avg_temp_c": row.avg_temp_c,
            "min_temp_c": row.min_temp_c,
            "max_temp_c": row.max_temp_c,
            "avg_humidity_pct": row.avg_humidity_pct,
            "max_humidity_pct": row.max_humidity_pct,
        }

    def did_humidity_exceed(self, device_id: str, threshold_pct: float, days_ago: int) -> bool:
        query = f"""
        SELECT COUNT(1) AS n
        FROM `{self._table(settings.indoor_table)}`
        WHERE device_id = @device_id
          AND DATE(event_ts) = DATE_SUB(CURRENT_DATE(), INTERVAL @days_ago DAY)
          AND humidity_pct > @threshold
        """
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("device_id", "STRING", device_id),
                bigquery.ScalarQueryParameter("days_ago", "INT64", int(days_ago)),
                bigquery.ScalarQueryParameter("threshold", "FLOAT64", float(threshold_pct)),
            ]
        )
        rows = list(self.client.query(query, job_config=job_config).result())
        if not rows:
            return False
        return bool(rows[0].n and rows[0].n > 0)

    @staticmethod
    def _compute_alerts(payload: IngestRequest) -> Dict[str, bool]:
        low_humidity = payload.indoor.humidity_pct < 40
        poor_air = False
        if payload.indoor.eco2_ppm is not None and payload.indoor.eco2_ppm > 1000:
            poor_air = True
        if payload.indoor.tvoc_ppb is not None and payload.indoor.tvoc_ppb > 500:
            poor_air = True
        return {"low_humidity": low_humidity, "poor_air_quality": poor_air}
