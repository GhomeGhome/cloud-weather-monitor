#!/usr/bin/env bash
# From repo root: load .env first, then run:
#   set -a && source .env && set +a
#   PROJECT_ID=your-project bash infra/deploy/deploy_api.sh
#
# Secrets are passed via --substitutions so you do not commit real keys in the YAML.
# Set SKIP_VERIFY=1 to skip post-deploy HTTP checks.

set -euo pipefail

: "${PROJECT_ID:?Missing PROJECT_ID — export it or put it in .env}"
: "${INGESTION_SHARED_SECRET:?Missing INGESTION_SHARED_SECRET — put it in .env and source .env}"
: "${OPENWEATHER_API_KEY:?Missing OPENWEATHER_API_KEY — put it in .env and source .env}"

REGION="${REGION:-europe-west6}"
SERVICE="${CLOUD_RUN_API_SERVICE:-weather-ingestion-api}"

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"

SUBST="_INGESTION_SHARED_SECRET=${INGESTION_SHARED_SECRET},_OPENWEATHER_API_KEY=${OPENWEATHER_API_KEY}"

if [[ -n "${OPENWEATHER_LAT:-}" ]]; then
  SUBST="${SUBST},_OPENWEATHER_LAT=${OPENWEATHER_LAT}"
fi
if [[ -n "${OPENWEATHER_LON:-}" ]]; then
  SUBST="${SUBST},_OPENWEATHER_LON=${OPENWEATHER_LON}"
fi

gcloud builds submit \
  --config=infra/cloudbuild.api.yaml \
  --project="${PROJECT_ID}" \
  --substitutions="${SUBST}" \
  .

if [[ "${SKIP_VERIFY:-0}" == "1" ]]; then
  echo "SKIP_VERIFY=1 — skipping HTTP checks."
  exit 0
fi

echo ""
echo "Verifying ${SERVICE} (${REGION})..."

BASE="$(
  gcloud run services describe "${SERVICE}" \
    --region="${REGION}" \
    --project="${PROJECT_ID}" \
    --format='value(status.url)' | tr -d '\r\n'
)"

if [[ -z "$BASE" ]]; then
  echo "ERROR: could not read status.url for ${SERVICE}." >&2
  exit 1
fi

echo "URL: ${BASE}"

# Do not use /healthz on public Cloud Run (can be handled by Google edge before your app).
ok_live=""
for _ in {1..12}; do
  if curl -sfS --max-time 15 "${BASE}/live" | grep -q '"status"'; then
    ok_live="yes"
    break
  fi
  sleep 5
done

if [[ -z "$ok_live" ]]; then
  echo "ERROR: GET ${BASE}/live did not return JSON with status within retry window." >&2
  echo "Hint: ensure roles/run.invoker includes allUsers if you need public access." >&2
  exit 1
fi

live_body="$(curl -sfS --max-time 15 "${BASE}/live")"
echo "GET /live: ${live_body}"

if ! echo "${live_body}" | grep -q '"status"'; then
  echo "ERROR: unexpected /live body." >&2
  exit 1
fi

root_body="$(curl -sfS --max-time 15 "${BASE}/")"
echo "GET /: ${root_body}"

if ! echo "${root_body}" | grep -q '"status":"alive"'; then
  echo "ERROR: GET / did not return expected JSON (service alive)." >&2
  exit 1
fi

echo ""
echo "OK — API is reachable. Use /live (not /healthz) for health checks on Cloud Run."
