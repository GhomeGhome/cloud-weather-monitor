# Cloud Analytics Weather Monitor

Indoor/outdoor weather monitoring platform using M5Stack Core2, Google Cloud, BigQuery, and Streamlit.

## Repository structure
- `device/`: device runtime (sensor read loop, local UI hooks, boot sync, voice announcement cooldown)
- `cloud_api/`: ingestion and read API for cloud persistence and recovery
- `dashboard/`: Streamlit dashboard for realtime and historical views
- `infra/`: BigQuery schema/queries and Cloud Build + Cloud Run deployment assets
- `docs/`: conventions, test plan, video checklist, and Q&A prep
- `tests/`: basic automated tests for critical logic

## Core features delivered
- Indoor sensor ingestion (temperature, humidity, TVOC, eCO2, motion)
- Outdoor weather integration via OpenWeatherMap
- BigQuery storage for indoor history, outdoor weather, and events/alerts
- Device boot sync from cloud latest state
- Alert logic:
  - low humidity when `< 40%`
  - poor air quality when `eCO2 > 1000` or `TVOC > 500`
- Streamlit dashboard with:
  - realtime metrics
  - historical charts
  - recent events/alerts
- Cloud deployment pipeline aligned with class labs:
  - Docker
  - Cloud Build
  - Artifact Registry
  - Cloud Run

## Hardware used
- M5Stack Core2 x2
- PIR Motion Unit x2
- ENV III Unit x2
- TVOC/eCO2 Gas Unit x1

## Environment setup
1. Copy and fill variables:
   ```bash
   cp .env.example .env
   ```
2. Export variables for local runs (`PROJECT_ID`, `DATASET_ID`, `INGESTION_SHARED_SECRET`, etc.).
3. Ensure GCP credentials are available (`GOOGLE_APPLICATION_CREDENTIALS`).

## BigQuery initialization
- Review and apply DDL from `infra/bigquery/schema.sql`.
- Reference queries in `infra/bigquery/queries.sql`.

## Local run

### API
```bash
cd cloud_api
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app:app --reload --port 8080
```

### Dashboard
```bash
cd dashboard
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

### Device simulation
```bash
cd device
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python main.py
```

## Cloud deployment
1. Setup services and Artifact Registry:
   ```bash
   bash infra/deploy/setup_gcp.sh
   ```
2. Deploy API:
   ```bash
   bash infra/deploy/deploy_api.sh
   ```
3. Deploy dashboard:
   ```bash
   bash infra/deploy/deploy_dashboard.sh
   ```

## Validation
- Run syntax checks:
  ```bash
  python3 -m compileall cloud_api dashboard device tests
  ```
- Run tests:
  ```bash
  pytest -q
  ```
- Follow scenario checklist in `docs/test-plan.md`.

## Deliverables support
- Video checklist: `docs/video-checklist.md`
- Presentation Q&A prep: `docs/presentation-qa.md`

## Team contributions
Add member names and ownership areas here before final submission.
