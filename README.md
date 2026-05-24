# Cloud Analytics — Weather Monitor

Station météo intérieure / extérieure : **M5Stack Core2**, **Google Cloud** (BigQuery, Cloud Run), **Streamlit**, météo **OpenWeatherMap**.

---

## Aperçu architecture

```
M5Stack (capteurs) ──POST /v1/ingest──► API Cloud Run ──► BigQuery
                                            ▲
Streamlit Cloud Run ────SELECT──────────────┘
```

- **API** : ingestion des mesures, météo, lecture du dernier état (boot device).
- **Dashboard** : uniquement lecture BigQuery (temps réel + historique + événements).
- **Secrets** : jamais dans Git — utiliser `.env` (local) et variables d’environnement Cloud Run.

---

## Déploiements (à compléter après chaque mise en prod)

Remplace par **tes** URLs une fois les services déployés :

| Service | Usage | URL (exemple) |
|--------|--------|----------------|
| API ingestion | `GET /live`, `POST /v1/ingest`, `GET /v1/device/{id}/latest` | `https://weather-ingestion-api-… .a.run.app` |
| Dashboard Streamlit | Interface publique pour le cours | `https://weather-dashboard-… .a.run.app` |

**Santé de l’API sur Cloud Run** : utiliser **`GET /live`** (ou **`GET /`**). Le chemin **`/healthz`** peut être intercepté par l’infrastructure avant ton application.

**Accès public** : après le premier déploiement, si `curl` renvoie **403**, ajouter le rôle **Cloud Run Invoker** pour **`allUsers`** sur chaque service concerné (Console GCP → Cloud Run → service → Permissions / IAM).

---

## Structure du dépôt

| Dossier | Rôle |
|---------|------|
| `cloud_api/` | API FastAPI (ingestion BigQuery, endpoints device / météo) |
| `dashboard/` | Application Streamlit |
| `device/` | Logique « device » (simulation locale ; à brancher sur UIFlow / Core2) |
| `infra/` | SQL BigQuery, `cloudbuild.*.yaml`, scripts `deploy_*.sh`, `setup_gcp.sh` |
| `docs/` | Conventions, plan de tests, checklist vidéo, préparation Q&A |
| `tests/` | Tests unitaires ciblés |
---

## Prérequis

- **Python 3.11+**
- **Compte Google Cloud** : projet avec facturation, APIs (BigQuery, Cloud Run, Artifact Registry, Cloud Build)
- **Google Cloud SDK** (`gcloud`) installé et authentifié
- Clé **OpenWeatherMap**
- Compte de service GCP + JSON pour le développement local (`GOOGLE_APPLICATION_CREDENTIALS`) — **ne pas commiter le JSON**

---

## Matériel

- M5Stack **Core2** ×2  
- **ENV III** ×2  
- **PIR Motion** ×2  
- **TVOC/eCO2** ×1  

---

## Configuration locale

```bash
cp .env.example .env
# Éditer .env : PROJECT_ID, DATASET_ID, INGESTION_SHARED_SECRET, OPENWEATHER_*, chemins credentials, etc.
```

Charger le `.env` avant les commandes locales :

```bash
set -a && source .env && set +a
```

---

## BigQuery

1. Créer le dataset (ex. `weather_analytics`) dans la console.  
2. Exécuter le DDL : `infra/bigquery/schema.sql` (adapter project/dataset si besoin).  
3. Requêtes d’exemple / reporting : `infra/bigquery/queries.sql`.

---

## Exécution locale

### API

```bash
cd cloud_api
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cd .. && set -a && source .env && set +a && cd cloud_api
uvicorn app:app --reload --port 8080
```

Swagger : http://127.0.0.1:8080/docs  

### Dashboard

```bash
cd dashboard
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cd .. && set -a && source .env && set +a && cd dashboard
streamlit run app.py
```

### Simulation device (sans Core2)

```bash
cd device
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
# Configurer API_BASE_URL et INGESTION_SHARED_SECRET dans l’environnement
python main.py
```

---

## Déploiement cloud (résumé)

Depuis la **racine** du dépôt, avec `.env` chargé (secrets ingestion + OpenWeather pour l’API) :

```bash
PROJECT_ID=ton-project-id bash infra/deploy/setup_gcp.sh   # une première fois (repo Artifact Registry, APIs)
set -a && source .env && set +a
export PROJECT_ID=ton-project-id
bash infra/deploy/deploy_api.sh
bash infra/deploy/deploy_dashboard.sh
```

Puis **IAM Invoker** pour accès public si nécessaire (voir tableaux ci-dessus).  
`SKIP_VERIFY=1` évite les vérifications HTTP post-build si besoin (`deploy_api.sh` / `deploy_dashboard.sh`).

---

## Test d’ingestion sans matériel

Exemple (secret lu depuis `.env`, URL lue depuis `gcloud`) :

```bash
cd /chemin/vers/group_project
set -a && source .env && set +a
export API_URL="$(gcloud run services describe weather-ingestion-api --region=europe-west6 --project=$PROJECT_ID --format='value(status.url)' | tr -d '\r\n')"
python3 -c "
import json, os, datetime
print(json.dumps({
  'secret': os.environ['INGESTION_SHARED_SECRET'],
  'device_id': 'core2-main',
  'timestamp': datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
  'indoor': {'temperature_c': 22.5, 'humidity_pct': 45.0, 'tvoc_ppb': 100, 'eco2_ppm': 600},
  'motion': {'detected': False, 'pir_sensor_id': 'pir-a'},
  'meta': {'firmware_version': '0.1.0', 'wifi_ssid': 'iot-unil'},
}))
" | curl -sS -X POST "${API_URL}/v1/ingest" -H "Content-Type: application/json" -d @-
```

---

## Qualité / tests

```bash
python3 -m compileall cloud_api dashboard device tests
pip install -r requirements-dev.txt   # si besoin
pytest -q
```

Scénarios manuels : **`docs/test-plan.md`**.

---

## Livrables cours

- **Vidéo** (YouTube non listée) : voir `docs/video-checklist.md`  
- **Soutenance** : `docs/presentation-qa.md`  
- Ne pas inclure **mots de passe, clés API, JSON de compte de service** dans le dépôt.

---

## Équipe

| Nom | Rôle / périmètre |
|-----|-----------------|
| Guillaume Grand | Cloud API (FastAPI), BigQuery, déploiement Cloud Run, firmware Core2 (MicroPython) |
| Alexandre Marlet | Dashboard Streamlit, infrastructure GCP, intégration Voice QA / OpenAI |
