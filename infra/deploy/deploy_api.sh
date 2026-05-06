#!/usr/bin/env bash
set -euo pipefail

: "${PROJECT_ID:?Missing PROJECT_ID}"

gcloud builds submit \
  --config=infra/cloudbuild.api.yaml \
  --project="${PROJECT_ID}" \
  .
