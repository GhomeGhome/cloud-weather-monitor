# Device to Cloud API Contract

## Endpoint
- `POST /v1/ingest`

## Request body
```json
{
  "secret": "shared-secret",
  "device_id": "core2-main",
  "timestamp": "2026-05-06T10:00:00Z",
  "indoor": {
    "temperature_c": 23.1,
    "humidity_pct": 41.2,
    "tvoc_ppb": 78,
    "eco2_ppm": 640
  },
  "motion": {
    "detected": true,
    "pir_sensor_id": "pir-a"
  },
  "meta": {
    "firmware_version": "0.1.0",
    "wifi_ssid": "home-network"
  }
}
```

## Responses
- `200`: accepted, includes inserted timestamp and active alerts.
- `401`: invalid shared secret.
- `422`: payload validation error.

## Boot sync endpoint
- `GET /v1/device/{device_id}/latest`
- Returns latest indoor and outdoor snapshot used by the device at startup.

## Weather endpoint (fallback)
- `GET /v1/weather/current`
- Returns latest weather from BigQuery and optionally fresh OpenWeather fetch.
