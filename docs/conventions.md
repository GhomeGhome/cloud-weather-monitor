# Project Conventions

## Cloud and naming
- Region: `europe-west6`
- BigQuery dataset: `weather_analytics` (override with env vars)
- Services:
  - API Cloud Run service: `weather-ingestion-api`
  - Dashboard Cloud Run service: `weather-dashboard`

## Architecture
- `device/`: M5Stack Core2 runtime (sensor collection + local UI + voice hooks)
- `cloud_api/`: ingestion and read endpoints for device boot sync
- `dashboard/`: Streamlit analytics UI backed by BigQuery
- `infra/`: SQL schemas and deploy scripts

## Configuration
- Never hardcode secrets in code.
- Use environment variables for all credentials and service IDs.
- Keep defaults safe for local development.

## Data cadence
- Sensor polling every `30-60s`.
- Ingestion to cloud every `60s` by default.
- Voice announcements with cooldown (`>= 1 hour`) unless critical alert.

## Alerts
- Humidity alert when `indoor_humidity < 40`.
- Air quality alert when `eco2 > 1000` or `tvoc > 500`.

## Operational behavior
- Device must boot with last known cloud values if sensors/API are unavailable.
- Dashboard queries BigQuery only; it does not ingest data.
