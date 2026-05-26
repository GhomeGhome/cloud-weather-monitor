# Cloud Weather Monitor

An indoor/outdoor weather station with a **voice AI assistant**, built on **M5Stack Core2**, **Google Cloud** (BigQuery, Cloud Run), **Streamlit**, **OpenWeatherMap**, and **OpenAI**.

**Demo video:** https://youtu.be/giZnkiv71Mo

**GitHub repo:** https://github.com/GhomeGhome/cloud-weather-monitor

**Live dashboard:** https://weather-dashboard-972242315876.europe-west6.run.app

---

## Architecture

```
M5Stack Core2 (ENV III + SGP30 + PIR + mic)
        │
        ├─ POST /v1/ingest ─────────────────► Cloud Run API ──► BigQuery
        ├─ POST /v1/pir/state ──────────────►       │
        └─ GET  /v1/device/{id}/answer ◄────────    │
                                                     │
Streamlit Dashboard (Cloud Run) ────────────────────┤
        ├─ SELECT ──────────────────────────► BigQuery
        ├─ POST /v1/qa  ────────────────────►       │
        ├─ POST /v1/stt (audio base64) ─────►       │ ──► OpenAI (Whisper / GPT / TTS)
        └─ POST /v1/tts ────────────────────►       │
                                                     └──► OpenWeatherMap
```

---

## Features

### API — FastAPI (Cloud Run)

- Secure sensor data ingestion from the Core2 (shared secret)
- Automatic alerts: low humidity (< 40 %), poor air quality (TVOC / eCO2)
- Outdoor weather: live data + 5-day forecast via OpenWeatherMap
- Voice QA pipeline: STT (Whisper) → BigQuery context → GPT answer → TTS
- PIR state relay between Core2 and Dashboard
- One-shot answer relay: Dashboard pushes QA answer, Core2 consumes it

### Dashboard — Streamlit (Cloud Run)

- Custom dark theme (CSS, glassmorphism)
- Real-time indoor metrics: temperature, humidity, TVOC, eCO2 (auto-refresh every 3 s)
- Live outdoor weather banner + animated icon
- 5-day forecast cards
- Historical charts per metric
- Event / alert log
- Voice QA interface: record → transcribe → ask → spoken answer
- Global alert banner with automatic detection

### Firmware — MicroPython on M5Stack Core2

- ENV III sensor: indoor temperature + humidity
- SGP30 sensor: TVOC (ppb) + eCO2 (ppm)
- PIR motion detection with IRQ interrupt and configurable cooldown
- Multi-network WiFi with automatic failover
- NTP time sync
- Periodic sensor push to the API (every 60 s)
- Voice QA: record audio → STT → display answer on screen
- Voice greeting triggered by motion (PIR)
- 3 display pages, warm colour palette

---

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/` | Basic liveness check |
| `GET` | `/live` | Liveness with timestamp (Cloud Run health check) |
| `POST` | `/v1/ingest` | Ingest a sensor reading from the Core2 |
| `GET` | `/v1/device/{id}/latest` | Latest known state for a device |
| `GET` | `/v1/weather/current` | Current outdoor weather (cached, `?refresh=true` to force) |
| `GET` | `/v1/weather/forecast` | N-day forecast (`?days=5`) |
| `POST` | `/v1/qa` | Text question → answer based on live BigQuery data |
| `POST` | `/v1/stt` | Base64 audio → text (OpenAI Whisper) |
| `POST` | `/v1/tts` | Text → base64 audio (OpenAI TTS) |
| `POST` | `/v1/pir/state` | Core2: report PIR state (`on` / `off`) |
| `GET` | `/v1/pir/state/{id}` | Dashboard: read current PIR state |
| `POST` | `/v1/device/{id}/answer` | Dashboard: push a QA answer to the device |
| `GET` | `/v1/device/{id}/answer` | Core2: consume the pending answer (one-shot) |

Interactive docs available at `/docs`.

---

## BigQuery — 4 tables

| Table | Content |
|-------|---------|
| `indoor_metrics` | Sensor readings (temp, humidity, TVOC, eCO2, PIR) — partitioned by date |
| `outdoor_weather` | OpenWeatherMap data + forecast JSON — partitioned by date |
| `device_events` | Alerts and system events (e.g. `ALERT_LOW_HUMIDITY`) |
| `latest_state` | Latest known state per device (upserted on each ingestion) |

---

## Repository Structure

```
cloud_api/
  app.py                  # FastAPI — all endpoints
  bigquery_repo.py        # BigQuery read / write
  config.py               # Settings via os.getenv() (no hardcoded secrets)
  models.py               # Pydantic schemas
  voice_qa_service.py     # STT / QA / TTS pipeline (OpenAI)
  weather_client.py       # OpenWeatherMap client
  requirements.txt
  Dockerfile

dashboard/
  app.py                  # Streamlit app (dark theme, Voice QA, alerts)
  charts.py               # Matplotlib dark-theme charts
  data.py                 # BigQuery queries for the dashboard
  requirements.txt
  Dockerfile

device/micropython/
  main.py                 # Core2 firmware (MicroPython)
  config_example.py       # Secrets template — copy to config.py and fill in
  config.py               # Gitignored — contains real WiFi credentials + INGEST_SECRET

infra/
  bigquery/schema.sql     # BigQuery table DDL
  bigquery/queries.sql    # Example queries
  cloudbuild.api.yaml     # Cloud Build pipeline — API
  cloudbuild.dashboard.yaml
  deploy/deploy_api.sh
  deploy/deploy_dashboard.sh
  deploy/setup_gcp.sh     # One-time GCP project setup
```

---

## Hardware

| Component | Qty | Purpose |
|-----------|-----|---------|
| M5Stack Core2 | ×2 | Main station (display, sensors, mic, speaker) |
| ENV III | ×2 | Indoor temperature + humidity |
| SGP30 | ×1 | Indoor air quality (TVOC / eCO2) |
| PIR Motion Unit | ×2 | Presence detection |

---

## Secrets & Configuration

### Backend / Dashboard

All keys are read from **environment variables** — never hardcoded.

```bash
cp .env.example .env
# Fill in: PROJECT_ID, DATASET_ID, INGESTION_SHARED_SECRET,
#          OPENWEATHER_API_KEY, OPENAI_API_KEY, GOOGLE_APPLICATION_CREDENTIALS
```

### Core2 Firmware

WiFi credentials and the shared secret are stored in a **gitignored** file:

```bash
cp device/micropython/config_example.py device/micropython/config.py
# Fill in INGEST_SECRET and WIFI_NETWORKS, then flash both files onto the Core2
```

### What is gitignored

| File / folder | Reason |
|---------------|--------|
| `.env` | All API keys and deployment secrets |
| `*.json` | GCP service account files |
| `device/micropython/config.py` | Core2 WiFi credentials + INGEST_SECRET |
| `.streamlit/secrets.toml` | Local Streamlit secrets |

---

## Running Locally

Load `.env` before each command:

```bash
set -a && source .env && set +a
```

### API

```bash
cd cloud_api
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app:app --reload --port 8080
# Swagger: http://127.0.0.1:8080/docs
```

### Dashboard

```bash
cd dashboard
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

---

## Cloud Deployment

Deployments are triggered automatically on every push to `main` via **Cloud Build**.

Manual deployment from the repo root:

```bash
# One-time GCP setup
PROJECT_ID=your-project-id bash infra/deploy/setup_gcp.sh

# Deploy
set -a && source .env && set +a
bash infra/deploy/deploy_api.sh
bash infra/deploy/deploy_dashboard.sh
```

### Live services

| Service | URL |
|---------|-----|
| Ingestion API | https://weather-ingestion-api-972242315876.europe-west6.run.app |
| Streamlit Dashboard | https://weather-dashboard-972242315876.europe-west6.run.app |

---

## Team

| Name | Contribution |
|------|-------------|
| Alexandre Marlet | Device firmware (M5Stack Core2, MicroPython, sensors, PIR, Voice QA on device) |
| Guillaume Grand | Cloud API (FastAPI), BigQuery, Cloud Run, Dashboard (Streamlit), OpenAI integration |
