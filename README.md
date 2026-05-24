# Cloud Analytics — Weather Monitor

Station météo intérieure/extérieure avec **assistant vocal IA** : **M5Stack Core2**, **Google Cloud** (BigQuery, Cloud Run), **Streamlit**, **OpenWeatherMap**, **OpenAI**.

---

## Architecture

```
M5Stack Core2 (ENV III + SGP30 + PIR + micro)
        │
        ├─ POST /v1/ingest ─────────────────► API Cloud Run ──► BigQuery
        ├─ POST /v1/pir/state ──────────────►     │
        └─ GET  /v1/device/{id}/answer ◄────────  │
                                                   │
Dashboard Streamlit Cloud Run ─────────────────────┤
        ├─ SELECT ──────────────────────────► BigQuery
        ├─ POST /v1/qa  ────────────────────►     │
        ├─ POST /v1/stt (audio base64) ─────►     │ ──► OpenAI (Whisper / TTS)
        ├─ POST /v1/tts ────────────────────►     │
        ├─ POST /v1/device/{id}/answer ─────►     │
        └─ GET  /v1/pir/state/{id} ─────────►     │
                                                   └──► OpenWeatherMap
```

---

## Fonctionnalités

### API — FastAPI (Cloud Run)

- **Ingestion** sécurisée des mesures (shared secret) depuis le Core2
- **Alertes automatiques** : humidité basse (< 40 %), qualité de l'air dégradée (TVOC/eCO2)
- **Météo extérieure** : données temps réel + prévisions sur 5 jours via OpenWeatherMap
- **Voice QA** : pipeline complet — STT (Whisper) → analyse des données BigQuery → réponse LLM → TTS
- **Coordination PIR** : relais d'état mouvement entre le Core2 et le Dashboard
- **Relay réponse** : le Dashboard pousse la réponse QA ; le Core2 la consomme en one-shot

### Dashboard — Streamlit (Cloud Run)

- Thème sombre custom (CSS Inter + glassmorphism)
- Métriques temps réel : température, humidité, TVOC, eCO2
- Bannière météo extérieure animée (soleil / neige / nuage selon conditions)
- Graphiques historiques par métrique (matplotlib dark theme)
- Journal des événements/alertes récents
- Interface Voice QA : enregistrement micro → transcription → question → réponse audio
- Bannière de détection mouvement PIR (polling toutes les secondes)
- Auto-refresh configurable

### Firmware Core2 — MicroPython UIFlow 1.x

- Lecture ENV III : température + humidité intérieures
- Lecture SGP30 : TVOC (ppb) + eCO2 (ppm)
- Détection mouvement PIR avec cooldown configurable
- Connexion WiFi multi-réseau avec failover automatique
- Synchronisation heure NTP (timezone configurable)
- Envoi périodique des mesures à l'API (toutes les 60 s)
- Voice QA : enregistrement audio → STT → affichage de la réponse sur écran
- 3 pages d'affichage (A = refresh, B = WiFi suivant, C = cycle pages)
- Palette de couleurs chaude/cozy (warm cream, sage green, soft coral…)

---

## Endpoints API

| Méthode | Chemin | Description |
|---------|--------|-------------|
| `GET` | `/` | Liveness basique (`{"status":"alive"}`) |
| `GET` | `/live` | Liveness avec timestamp — **utiliser pour Cloud Run health check** |
| `POST` | `/v1/ingest` | Ingestion d'une mesure depuis Core2 (secret requis) |
| `GET` | `/v1/device/{id}/latest` | Dernier état connu d'un device |
| `GET` | `/v1/weather/current` | Météo extérieure courante (cache BigQuery, `?refresh=true` pour forcer) |
| `GET` | `/v1/weather/forecast` | Prévisions sur N jours (`?days=5`) |
| `POST` | `/v1/qa` | Question textuelle → réponse basée sur BigQuery |
| `POST` | `/v1/stt` | Audio base64 → texte (OpenAI Whisper) |
| `POST` | `/v1/tts` | Texte → audio base64 (OpenAI TTS) |
| `POST` | `/v1/pir/state` | Core2 : déclare état PIR (`on`/`off`) |
| `GET` | `/v1/pir/state/{id}` | Dashboard : lit l'état PIR courant |
| `POST` | `/v1/device/{id}/answer` | Dashboard : pousse une réponse QA vers le device |
| `GET` | `/v1/device/{id}/answer` | Core2 : consomme la réponse en attente (one-shot) |

> Swagger disponible sur `/docs` en local.
> ⚠️ Ne pas utiliser `/healthz` sur Cloud Run — ce chemin peut être intercepté par l'infra Google avant l'application.

---

## BigQuery — 4 tables

| Table | Contenu |
|-------|---------|
| `indoor_metrics` | Mesures capteurs (temp, humidité, TVOC, eCO2, PIR) — partitionné par date |
| `outdoor_weather` | Données OpenWeatherMap + prévisions JSON — partitionné par date |
| `device_events` | Alertes et événements système (ex. `ALERT_LOW_HUMIDITY`) |
| `latest_state` | Dernier état connu par device (upsert à chaque ingestion) |

---

## Structure du dépôt

```
cloud_api/
  app.py                  # API FastAPI — tous les endpoints
  bigquery_repo.py        # Accès BigQuery (lecture / écriture)
  config.py               # Settings via os.getenv() (aucun secret en dur)
  models.py               # Schémas Pydantic (IngestRequest, QaRequest, …)
  voice_qa_service.py     # Pipeline STT / QA / TTS (OpenAI)
  weather_client.py       # Client OpenWeatherMap (current + forecast)
  requirements.txt
  Dockerfile

dashboard/
  app.py                  # Application Streamlit (dark theme, Voice QA, PIR)
  charts.py               # Graphiques matplotlib dark theme
  data.py                 # Requêtes BigQuery pour le dashboard
  requirements.txt
  Dockerfile

device/micropython/
  core2_main.py           # Firmware principal Core2 v1.2 (UIFlow1 MicroPython)
  config_example.py       # Template secrets → copier en config.py et remplir
  config.py               # ⛔ Gitignored — contient WiFi + INGEST_SECRET réels
  test_mic.py             # Diagnostic I2S microphone
  test_mic2.py            # Test enregistrement PDM + lecture
  test_mic3.py            # Vérification survie WAV après reboot
  test_speaker.py         # Inspection objet speaker + test méthodes

infra/
  bigquery/schema.sql     # DDL des 4 tables BigQuery
  bigquery/queries.sql    # Requêtes de reporting / exemples
  cloudbuild.api.yaml     # Cloud Build — build + déploiement API
  cloudbuild.dashboard.yaml
  deploy/deploy_api.sh    # Script déploiement API (source .env avant)
  deploy/deploy_dashboard.sh
  deploy/setup_gcp.sh     # Init Artifact Registry + APIs GCP (une seule fois)

docs/
  test-plan.md            # Scénarios de test manuels
  video-checklist.md      # Checklist vidéo de présentation
  presentation-qa.md      # Préparation soutenance / Q&A

tests/                    # Tests unitaires
exemple_uiflow2.py        # Référence UIFlow2 (credentials remplacés par placeholders)
```

---

## Prérequis

- **Python 3.11+**
- **Compte Google Cloud** : projet avec facturation, APIs activées (BigQuery, Cloud Run, Artifact Registry, Cloud Build)
- **Google Cloud SDK** (`gcloud`) installé et authentifié (`gcloud auth login`)
- Clé **OpenWeatherMap** (gratuite)
- Clé **OpenAI** (Whisper + TTS)
- Compte de service GCP + JSON pour le dev local (`GOOGLE_APPLICATION_CREDENTIALS`) — **ne pas commiter le JSON**
- M5Stack Core2 + ENV III + SGP30 + PIR Motion (pour la démo physique)

---

## Matériel

| Composant | Qté | Usage |
|-----------|-----|-------|
| M5Stack Core2 | ×2 | Station principale (affichage, capteurs, micro) |
| ENV III | ×2 | Température + humidité intérieures |
| SGP30 (TVOC/eCO2) | ×1 | Qualité de l'air intérieur |
| PIR Motion | ×2 | Détection de présence |

---

## Secrets & configuration

### Backend / Dashboard

Toutes les clés sont lues depuis des **variables d'environnement** (jamais en dur dans le code).

```bash
cp .env.example .env
# Remplir : PROJECT_ID, DATASET_ID, INGESTION_SHARED_SECRET,
#           OPENWEATHER_API_KEY, OPENAI_API_KEY, GOOGLE_APPLICATION_CREDENTIALS…
```

### Firmware Core2

Les secrets WiFi et le shared secret sont dans un fichier **gitignored** :

```bash
cp device/micropython/config_example.py device/micropython/config.py
# Remplir INGEST_SECRET et WIFI_NETWORKS, puis flasher config.py + core2_main.py
```

`core2_main.py` utilise `try: from config import … except ImportError: …` pour rester lisible sans secrets sur GitHub.

### Ce qui est gitignored

| Fichier / dossier | Raison |
|-------------------|--------|
| `.env` | Toutes les clés API et secrets de déploiement |
| `*.json` | Fichiers de compte de service GCP |
| `device/micropython/config.py` | WiFi + INGEST_SECRET du Core2 |
| `.streamlit/secrets.toml` | Secrets Streamlit local |

---

## Exécution locale

Charger `.env` avant chaque commande :

```bash
set -a && source .env && set +a
```

### API

```bash
cd cloud_api
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app:app --reload --port 8080
# → Swagger : http://127.0.0.1:8080/docs
```

### Dashboard

```bash
cd dashboard
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

### Simulation device (sans Core2)

```bash
set -a && source .env && set +a
export API_URL="https://weather-ingestion-api-972242315876.europe-west6.run.app"
python3 -c "
import json, os, datetime
print(json.dumps({
  'secret': os.environ['INGESTION_SHARED_SECRET'],
  'device_id': 'core2-main',
  'timestamp': datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
  'indoor': {'temperature_c': 22.5, 'humidity_pct': 45.0, 'tvoc_ppb': 100, 'eco2_ppm': 600},
  'motion': {'detected': False, 'pir_sensor_id': 'pir-a'},
  'meta': {'firmware_version': '1.2.0', 'wifi_ssid': 'iot-unil'},
}))
" | curl -sS -X POST "${API_URL}/v1/ingest" -H "Content-Type: application/json" -d @-
```

---

## Déploiement cloud

Depuis la **racine** du dépôt :

```bash
# 1. Initialiser le projet GCP (une seule fois)
PROJECT_ID=ton-project-id bash infra/deploy/setup_gcp.sh

# 2. Charger les secrets
set -a && source .env && set +a
export PROJECT_ID=ton-project-id

# 3. Déployer l'API et le Dashboard
bash infra/deploy/deploy_api.sh
bash infra/deploy/deploy_dashboard.sh
```

**Accès public** : si `curl` renvoie 403 après déploiement, ajouter le rôle **Cloud Run Invoker** pour `allUsers` (Console GCP → Cloud Run → service → Permissions).

`SKIP_VERIFY=1` permet de passer les vérifications HTTP post-build :

```bash
SKIP_VERIFY=1 bash infra/deploy/deploy_api.sh
```

### Services déployés

| Service | URL |
|---------|-----|
| API ingestion | `https://weather-ingestion-api-972242315876.europe-west6.run.app` |
| Dashboard Streamlit | `https://weather-dashboard-u2swu65boa-oa.a.run.app` |

---

## BigQuery — setup

```bash
# 1. Créer le dataset dans la console GCP (ex. weather_analytics)
# 2. Exécuter le DDL (adapter project/dataset si besoin)
bq query --use_legacy_sql=false < infra/bigquery/schema.sql
# 3. Requêtes d'exemple : infra/bigquery/queries.sql
```

---

## Qualité / tests

```bash
python3 -m compileall cloud_api dashboard device tests
pip install -r requirements-dev.txt
pytest -q
```

Scénarios manuels : `docs/test-plan.md`.

---

## Livrables cours

- **Vidéo** (YouTube non listée) : voir `docs/video-checklist.md`
- **Soutenance** : `docs/presentation-qa.md`
- Aucun mot de passe, clé API ou JSON de compte de service dans le dépôt.

---

## Équipe

| Nom | Rôle / périmètre |
|-----|-----------------|
| Guillaume Grand | Cloud API (FastAPI), BigQuery, déploiement Cloud Run, firmware Core2 (MicroPython) |
| Alexandre Marlet | Dashboard Streamlit, infrastructure GCP, intégration Voice QA / OpenAI |
