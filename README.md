# ECO-SURVEILLANCE MALI

> Plateforme intelligente de surveillance environnementale multi-source du Mali.

## Vision

ECO-SURVEILLANCE MALI centralise des donnees environnementales provenant de sources satellitaires, climatiques, geospatiales et de stations environnementales afin de detecter des anomalies, evaluer les risques, generer des incidents et calculer un **Indice Environnemental de Zone (IEZ)**.

## Stack

### Backend
- Python 3.12
- Django 4.2
- Django Templates + Django ORM
- PostgreSQL / PostGIS (prod) — SQLite (dev)
- Celery + Redis

### Frontend
- Django Templates
- HTML / CSS / JavaScript
- Tailwind CSS (CDN)
- Leaflet.js (carte)
- Chart.js (graphiques)

### Donnees
- NASA FIRMS (feux)
- Sentinel-2 (vegetation)
- Sentinel-5P (atmosphere)
- NASA POWER (climat)
- ERA5, CHIRPS (climat)
- OpenAQ (qualite air)
- Capteurs IoT simules

### IA
- Groq API (llama-3.3-70b-versatile)

## Installation

```bash
# Cloner
git clone https://github.com/Kane005005/ECO-SURVEILLANCE.git
cd ECO-SURVEILLANCE

# Environnement virtuel
python3 -m venv venv
source venv/bin/activate

# Dependances
pip install -r requirements.txt

# Configuration
cp .env.example .env
# Modifier .env selon vos besoins

# Base de donnees
python manage.py migrate

# Superuser
python manage.py createsuperuser

# Donnees de demonstration
python manage.py load_demo_data

# Serveur
python manage.py runserver
```

## Variables d'environnement

| Variable | Defaut | Description |
|---|---|---|
| `DJANGO_SECRET_KEY` | change-me | Cle secrete Django |
| `DJANGO_DEBUG` | 1 | Mode debug |
| `USE_SQLITE` | 1 | Utiliser SQLite (dev) |
| `DATABASE_NAME` | eco_surveillance | Nom base PostgreSQL |
| `FIRMS_MAP_KEY` | | Cle NASA FIRMS |
| `GROQ_API_KEY` | | Cle API Groq |
| `OPENAQ_API_KEY` | | Cle API OpenAQ |

## Structure

```
ECO-SURVEILLANCE/
├── config/                 # Configuration Django
├── apps/                   # Applications Django
│   ├── core/               # Noyau, dashboard, API
│   ├── users/              # Utilisateurs
│   ├── geography/          # Zones, regions, communes
│   ├── fires/              # Feux (NASA FIRMS)
│   ├── vegetation/         # NDVI, vegetation
│   ├── water/              # Eau, qualite
│   ├── climate/            # Climat, precipitations
│   ├── atmosphere/         # Atmosphere, polluants
│   ├── sensors/            # Stations, capteurs
│   ├── anomalies/          # Detection d'anomalies
│   ├── risk/               # Moteur de risques
│   ├── iez/                # Indice Environnemental de Zone
│   ├── incidents/          # Incidents
│   ├── alerts/             # Alertes
│   ├── ai/                 # Intelligence artificielle
│   ├── satellite/          # Observations satellite
│   └── reports/            # Rapports
├── core/                   # Moteurs (anomaly, risk, iez)
├── data_providers/         # Providers de donnees
├── ai/                     # Providers IA
├── templates/              # Templates HTML
├── static/                 # Fichiers statiques
├── logo/                   # Branding
└── manage.py
```

## Applications Django

| App | Modeles | Description |
|---|---|---|
| `core` | DataSource | Noyau, dashboard, API |
| `users` | User | Utilisateurs et roles |
| `geography` | Country, Region, Circle, Commune, MonitoringZone | Geographie |
| `fires` | FireDetection | Feux actifs |
| `vegetation` | VegetationObservation | NDVI, indices |
| `water` | WaterBody, WaterObservation | Qualite de l'eau |
| `climate` | ClimateObservation | Donnees climatiques |
| `atmosphere` | AtmosphericObservation | Polluants atmospheriques |
| `sensors` | MonitoringStation, Sensor, SensorReading | Stations et capteurs |
| `anomalies` | Anomaly | Detection d'anomalies |
| `risk` | RiskAssessment | Moteur de risques |
| `iez` | IEZCalculation | Indice Environnemental de Zone |
| `incidents` | Incident | Gestion des incidents |
| `alerts` | Alert | Systeme d'alertes |
| `ai` | AIAnalysis | Analyses IA |
| `satellite` | SatelliteObservation | Observations satellite |
| `reports` | Report | Rapports |

## URLs

| URL | Description |
|---|---|
| `/` | Accueil |
| `/dashboard/` | Dashboard national |
| `/map/` | Carte interactive |
| `/zones/` | Liste des zones |
| `/stations/` | Stations environnementales |
| `/incidents/` | Incidents |
| `/fires/` | Detections de feux |
| `/alerts/` | Alertes |
| `/anomalies/` | Anomalies |
| `/risk/` | Evaluations de risques |
| `/vegetation/` | Observations vegetation |
| `/water/` | Corps d'eau |
| `/climate/` | Observations climatiques |
| `/atmosphere/` | Observations atmospheriques |
| `/satellite/` | Observations satellite |
| `/iez/` | Calculs IEZ |
| `/ai/` | Analyses IA |
| `/reports/` | Rapports |
| `/admin/` | Administration Django |

## Mode DEMO

Le mode DEMO genere des donnees simulees pour tester toutes les fonctionnalites.

```bash
python manage.py load_demo_data
```

Donnees generees :
- 12 zones de surveillance
- 24 stations simulees (144 capteurs)
- 360 observations vegetation (NDVI)
- 1440 observations climatiques
- 720 observations atmospheriques
- 720 observations eau
- 1008 lectures capteurs
- 60 detections de feux
- 59 anomalies
- 72 evaluations de risques
- 8 incidents
- 12 calculs IEZ
- 8 sources de donnees

## Admin

Acces : `http://localhost:8000/admin/`

Tous les modeles sont enregistres dans l'admin avec filtres et recherches.

## Tests

```bash
python manage.py test
```

## Celery

```bash
# Worker
celery -A config worker -l info

# Beat (taches periodiques)
celery -A config beat -l info
```

## Feuilles de route

- [x] Architecture Django
- [x] Modeles de donnees
- [x] Base de donnees
- [x] Dashboard
- [x] Carte interactive
- [x] Stations simulees
- [x] Moteur d'anomalies
- [x] Moteur de risques
- [x] IEZ
- [x] Incidents et alertes
- [x] Donnees DEMO
- [x] Administration Django
- [ ] Integration NASA FIRMS reelle
- [ ] Integration Sentinel-2
- [ ] Integration NASA POWER
- [ ] Taches Celery periodiques
- [ ] Tests completes
- [ ] PDF rapports
- [ ] Authentification complete
- [ ] Notifications email/SMS
