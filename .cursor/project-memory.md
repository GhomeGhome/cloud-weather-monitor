# Cloud Analytics Project - Memo de reference

## Contexte
- Projet: moniteur meteo indoor/outdoor avec appareil M5Stack Core2 + dashboard cloud.
- Objectif: collecter des donnees capteurs locaux + meteo externe, stocker l'historique, afficher en local et a distance.
- Exigence forte: code compris de bout en bout par l'equipe (Q&A final type examen).

## Exigences fonctionnelles (obligatoires)
- Affichage sur M5Stack:
  - temperature exterieure
  - temperature et humidite interieures
  - qualite de l'air interieure
  - date/heure (NTP)
  - prevision meteo sur plusieurs jours (pas necessairement stockee en cloud)
- Presence (PIR): annoncer des updates/alertes vocales utiles sans spam (ex: max 1 annonce/heure).
- Donnees historiques stockees dans BigQuery:
  - mesures indoor (temp/humidite/air quality)
  - historique meteo exterieure
- Dashboard Streamlit cloud:
  - lit les donnees depuis BigQuery
  - vue temps reel + historique (courbes, etats, tendances)
- Au reboot/perte internet:
  - recuperer les dernieres valeurs depuis BigQuery
  - les afficher directement sur l'appareil
- Possibilite de changer les credentials Wi-Fi depuis l'UI (point explicitement teste).

## Integrations techniques attendues
- BigQuery pour persistance.
- OpenWeatherMap (ou equivalent) pour meteo externe + icones.
- Speech-to-Text + Text-to-Speech (Google ou OpenAI).
- LLM (Google/OpenAI) pour variantes de reponses conversationnelles.
- Architecture en 3 couches:
  - data (BigQuery)
  - services/middleware (logique + acces donnees)
  - UI (M5Stack + Streamlit)

## Regles/qualite a respecter
- Variables de config abstraites (wifi, zip/location, endpoints GCP, cles API, etc.).
- Pas de secrets dans le repo (env vars + fichiers ignores).
- Code modulaire (pas tout dans un seul fichier).
- Application stable avec gestion des cas limites (offline, reboot, erreurs API).
- README clair: deploiement, architecture, contenu des dossiers, roles des membres.
- Niveau de polish eleve attendu sur UI/UX et finition generale.
- Volume de code attendu: >1000 lignes (contexte 2026 avec usage GenAI).

## Livrables
- Video YouTube non listee (3-10 min), sans montrer le code, avec voix humaine de l'equipe + visages.
- Repo GitHub avec lien video, README complet et contributions individuelles explicites.
- Zip du repo a remettre sur Moodle.
- Presentation live finale: demonstration + defense technique detaillee.

## Criteres d'evaluation (resume)
- Features & code quality: 40%
- Interface quality: 20%
- Git/reproducibilite: 20%
- Video quality: 20%

## Materiel disponible (contraintes du projet actuel)
- M5Stack Core2: 2 unites
- PIR Motion Unit: 2 unites
- ENV III Unit: 2 unites
- TVOC/eCO2 Gas Unit: 1 unite

## Implications pratiques pour l'implementation
- Mesures indoor minimales:
  - temperature + humidite via ENV III
  - qualite d'air via TVOC/eCO2
  - presence via PIR
- Une frequence d'acquisition claire doit etre definie (ex: toutes les 30-60 s) et dissociee de la frequence d'annonces vocales.
- Ajouter un mecanisme de "cooldown" des annonces vocales (ex: horodatage derniere annonce).
- Prevoir un mode "degrade" si API meteo indisponible (afficher dernieres valeurs connues + statut erreur).
- Prioriser un schema BigQuery simple et requetable pour le dashboard (timestamps explicites + source des donnees).

## TODO de cadrage rapide
- Choisir stack exacte middleware (ex: Python + FastAPI/Flask).
- Definir schema BigQuery (tables indoor/outdoor/events).
- Definir contrat API interne (device <-> cloud).
- Concevoir maquette UI M5Stack (petit ecran) et Streamlit (historique).
- Mettre en place gestion config/secrets et script de setup.
