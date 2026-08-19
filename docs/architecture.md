# Architecture — ECO-SURVEILLANCE MALI

## Pipeline

```
DATA SOURCES → INGESTION → NORMALISATION → OBSERVATIONS → INDICES → ANOMALIES → RISQUES → IEZ → ALERTES/INCIDENTS → DASHBOARD
```

## Stack

- **Backend**: Django 4.2 + Django ORM + SQLite (dev) / PostgreSQL+PostGIS (prod)
- **Frontend**: Django Templates + Tailwind CDN + Leaflet + Chart.js
- **Async**: Celery + Redis
- **AI**: Groq API (Llama 3.3 70B)
- **Satellite**: Copernicus CDSE (Sentinel-2, Sentinel-5P), NASA FIRMS, NASA POWER, CHIRPS, Landsat

## Apps

| App | Modèle principal | Rôle |
|---|---|---|
| `geography` | MonitoringZone | Hub central — toutes les données sont liées à une zone |
| `fires` | FireDetection | Détections de feux (FIRMS) |
| `vegetation` | VegetationObservation | Indices végétaux (NDVI, NDWI, NBR, NDMI) |
| `water` | WaterBody, WaterObservation | Corps d'eau + observations |
| `climate` | ClimateObservation | Données climatiques (temp, pluie, hum, vent) |
| `atmosphere` | AtmosphericObservation | Données atmosphériques (SO2, O3, AER_AI, NO2) |
| `sensors` | MonitoringStation, Sensor | Capteurs IoT (simulés MVP) |
| `anomalies` | Anomaly | Détection d'anomalies |
| `risk` | RiskAssessment | Évaluation de risques |
| `incidents` | Incident | Incidents environnementaux |
| `alerts` | Alert | Alertes automatiques |
| `iez` | IEZCalculation | Indice Environnemental de Zone |
| `satellite` | SatelliteObservation | Observations satellite |
| `ai` | AIAnalysis | Analyses IA (Groq) |
| `reports` | Report | Rapports générés |

## Data Providers

| Provider | Source | Auth | Status |
|---|---|---|---|
| `FIRMSProvider` | NASA FIRMS | API Key | Fonctionnel |
| `NASAPowerProvider` | NASA POWER | Open access | Fonctionnel |
| `CHIRPSProvider` | CHIRPS UCSB | Open access | Fonctionnel |
| `Sentinel2Provider` | Copernicus CDSE | OAuth2 | Fonctionnel |
| `Sentinel5PProvider` | Copernicus CDSE | OAuth2 | Fonctionnel |
| `LandsatProvider` | AWS S3 USGS | Requester Pays | Complémentaire |

## Engines

### AnomalyEngine
- Z-score: |z| < 1.5 → NONE, < 2.5 → LOW, < 4.0 → MEDIUM, ≥ 4.0 → HIGH, ≥ 6.0 → CRITICAL
- Directionnel: supporte 'above', 'below', 'any'
- Multi-signal: agrège plusieurs signaux

### RiskEngine
- Types: WILDFIRE, DROUGHT, VEGETATION_DEGRADATION, WATER_POLLUTION, WATER_STRESS, HEAT, ATMOSPHERIC_ANOMALY
- Score 0-100 avec pondérations par type
- Facteurs explicables et reproductibles
- Niveaux: GREEN (<25), YELLOW (25-50), ORANGE (50-80), RED (≥80)

### IEZEngine
- 7 dimensions: vegetation, water, climate, fire, atmosphere, human_pressure, vulnerability
- Score 0-100, classes: BON (≥85), VIGILANCE (≥65), DÉGRADÉ (≥40), CRITIQUE (<40)
- Pondérations configurables

### AlertEngine
- Règles basées sur seuils et combinaisons de signaux
- Types: HIGH_FIRE_RISK, ACTIVE_FIRES, DROUGHT_WARNING, EXTREME_HEAT, VEGETATION_DECLINE, WATER_POLLUTION, ATMOSPHERIC_POLLUTION
- Déduplication temporelle (24h)

## Celery Tasks

| Task | Périodicité | Description |
|---|---|---|
| `sync_firms_data` | 6h | Sync FIRMS |
| `sync_nasa_power` | 1j | Sync climate |
| `simulate_all_stations` | 1h | Simulation capteurs |
| `run_anomaly_detection` | 12h | Détection anomalies |
| `compute_all_iez` | 1j | Calcul IEZ |
| `evaluate_all_alerts` | 6h | Évaluation alertes |
| `compute_all_risks` | (manuel) | Calcul risques |

## DEMO vs REAL

- `DEMO_MODE=1`: données simulées, providers stubs retournent des valeurs aléatoires
- `DEMO_MODE=0`: providers appellent les APIs réelles (FIRMS, POWER, CDSE)
- Chaque observation porte `is_simulated` pour distinguer

## Variables d'environnement critiques

```
FIRMS_MAP_KEY=          # NASA FIRMS API key
CDSE_CLIENT_ID=         # Copernicus OAuth2
CDSE_CLIENT_SECRET=     # Copernicus OAuth2
GROQ_API_KEY=           # Groq AI
```
