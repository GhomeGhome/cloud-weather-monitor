-- Dataset: create `weather_analytics` in project weather-monitor-495511 before running (or use an existing one).
-- Replace project/dataset if your teammate uses a different GCP project.

CREATE TABLE IF NOT EXISTS `weather-monitor-495511.weather_analytics.indoor_metrics` (
  event_ts TIMESTAMP NOT NULL,
  device_id STRING NOT NULL,
  temperature_c FLOAT64,
  humidity_pct FLOAT64,
  tvoc_ppb INT64,
  eco2_ppm INT64,
  motion_detected BOOL,
  pir_sensor_id STRING,
  firmware_version STRING,
  wifi_ssid STRING,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP()
)
PARTITION BY DATE(event_ts)
CLUSTER BY device_id;

CREATE TABLE IF NOT EXISTS `weather-monitor-495511.weather_analytics.outdoor_weather` (
  weather_ts TIMESTAMP NOT NULL,
  source STRING NOT NULL,
  lat FLOAT64,
  lon FLOAT64,
  temperature_c FLOAT64,
  humidity_pct FLOAT64,
  pressure_hpa FLOAT64,
  wind_speed_ms FLOAT64,
  weather_main STRING,
  weather_description STRING,
  weather_icon STRING,
  forecast_json STRING,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP()
)
PARTITION BY DATE(weather_ts)
CLUSTER BY source;

CREATE TABLE IF NOT EXISTS `weather-monitor-495511.weather_analytics.device_events` (
  event_ts TIMESTAMP NOT NULL,
  device_id STRING NOT NULL,
  event_type STRING NOT NULL,
  severity STRING,
  message STRING,
  payload_json STRING,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP()
)
PARTITION BY DATE(event_ts)
CLUSTER BY device_id, event_type;

CREATE TABLE IF NOT EXISTS `weather-monitor-495511.weather_analytics.latest_state` (
  device_id STRING NOT NULL,
  updated_at TIMESTAMP NOT NULL,
  indoor_json STRING,
  outdoor_json STRING,
  status_json STRING
);
