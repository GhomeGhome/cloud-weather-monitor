#!/usr/bin/env bash
set -euo pipefail

# Required env vars: PROJECT_ID, REGION, REPO
: "${PROJECT_ID:?Missing PROJECT_ID}"
: "${REGION:=europe-west6}"
: "${REPO:=weather-repo}"

gcloud config set project "${PROJECT_ID}"
gcloud services enable \
  artifactregistry.googleapis.com \
  cloudbuild.googleapis.com \
  run.googleapis.com \
  bigquery.googleapis.com

gcloud artifacts repositories create "${REPO}" \
  --repository-format=docker \
  --location="${REGION}" \
  --description="Weather monitor images" || true

echo "GCP setup complete."
