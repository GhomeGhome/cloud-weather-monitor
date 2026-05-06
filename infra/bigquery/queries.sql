-- Latest indoor values per device
SELECT
  device_id,
  ARRAY_AGG(
    STRUCT(
      event_ts,
      temperature_c,
      humidity_pct,
      tvoc_ppb,
      eco2_ppm,
      motion_detected
    )
    ORDER BY event_ts DESC LIMIT 1
  )[OFFSET(0)] AS latest
FROM `weather-monitor-495511.weather_analytics.indoor_metrics`
GROUP BY device_id;

-- Indoor hourly aggregates for dashboard history
SELECT
  TIMESTAMP_TRUNC(event_ts, HOUR) AS hour_ts,
  device_id,
  AVG(temperature_c) AS avg_temp_c,
  AVG(humidity_pct) AS avg_humidity_pct,
  AVG(tvoc_ppb) AS avg_tvoc_ppb,
  AVG(eco2_ppm) AS avg_eco2_ppm
FROM `weather-monitor-495511.weather_analytics.indoor_metrics`
WHERE event_ts BETWEEN @start_ts AND @end_ts
GROUP BY hour_ts, device_id
ORDER BY hour_ts ASC;

-- Latest outdoor weather
SELECT
  weather_ts,
  temperature_c,
  humidity_pct,
  weather_main,
  weather_description,
  weather_icon
FROM `weather-monitor-495511.weather_analytics.outdoor_weather`
ORDER BY weather_ts DESC
LIMIT 1;

-- Alert rows for humidity < 40 and poor air quality
SELECT
  event_ts,
  device_id,
  humidity_pct,
  tvoc_ppb,
  eco2_ppm,
  CASE
    WHEN humidity_pct < 40 THEN 'LOW_HUMIDITY'
    WHEN eco2_ppm > 1000 OR tvoc_ppb > 500 THEN 'POOR_AIR_QUALITY'
    ELSE 'NONE'
  END AS alert_type
FROM `weather-monitor-495511.weather_analytics.indoor_metrics`
WHERE event_ts BETWEEN @start_ts AND @end_ts
  AND (
    humidity_pct < 40
    OR eco2_ppm > 1000
    OR tvoc_ppb > 500
  )
ORDER BY event_ts DESC;

-- Startup sync for one device (latest indoor + latest outdoor)
-- Each subquery must return a single column (here: JSON string).
SELECT
  (
    SELECT TO_JSON_STRING(STRUCT(
      event_ts,
      temperature_c,
      humidity_pct,
      tvoc_ppb,
      eco2_ppm,
      motion_detected
    ))
    FROM `weather-monitor-495511.weather_analytics.indoor_metrics`
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
    FROM `weather-monitor-495511.weather_analytics.outdoor_weather`
    ORDER BY weather_ts DESC
    LIMIT 1
  ) AS outdoor_json;
