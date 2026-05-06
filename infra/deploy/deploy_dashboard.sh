#!/usr/bin/env bash
set -euo pipefail

: "${PROJECT_ID:?Missing PROJECT_ID}"

REGION="${REGION:-europe-west6}"
SERVICE="${CLOUD_RUN_DASHBOARD_SERVICE:-weather-dashboard}"

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"

gcloud builds submit \
  --config=infra/cloudbuild.dashboard.yaml \
  --project="${PROJECT_ID}" \
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

# Streamlit returns HTML on / ; wait for cold start then require HTTP 200.
http_ok=""
for _ in {1..12}; do
  code="$(curl -sS -o /dev/null -w "%{http_code}" --max-time 20 "${BASE}/" || true)"
  if [[ "${code}" == "200" ]]; then
    http_ok="yes"
    break
  fi
  sleep 5
done

if [[ -z "$http_ok" ]]; then
  echo "ERROR: GET ${BASE}/ did not return HTTP 200 within retry window (last code was: ${code:-none})." >&2
  echo "Hint: add allUsers as roles/run.invoker if the dashboard must be public." >&2
  exit 1
fi

echo "GET / → HTTP 200"
echo ""
echo "OK — dashboard is reachable at ${BASE}"
