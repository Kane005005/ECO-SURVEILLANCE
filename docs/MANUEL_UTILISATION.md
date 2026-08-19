# ECO-SURVEILLANCE MALI
## Manuel d'Utilisation et Rapport Fonctionnel
### Version 1.0 — Août 2026

---

## Table des matières

1. [Présentation Générale](#1-présentation-générale)
2. [Architecture Technique](#2-architecture-technique)
3. [Sources de Données](#3-sources-de-données)
4. [Moteurs d'Analyse](#4-moteurs-danalyse)
5. [Interface Utilisateur — Dashboard](#5-interface-utilisateur--dashboard)
6. [API REST — Guide Complet](#6-api-rest--guide-complet)
7. [Tâches Automatisées](#7-tâches-automatisées)
8. [Guide d'Installation](#8-guide-dinstallation)
9. [Configuration](#9-configuration)
10. [Glossaire](#10-glossaire)

---

## 1. Présentation Générale

### 1.1 Qu'est-ce qu'ECO-SURVEILLANCE ?

**ECO-SURVEILLANCE** est un système de surveillance environnementale intégré conçu pour le Mali et la sous-région UEMOA. Il collecte automatiquement des données satellitaires, climatiques et atmosphériques en temps réel, les analyse à l'aide de moteurs computationnels et d'intelligence artificielle, et produit des alertes précoces pour les décideurs.

### 1.2 Problème Résolu

Le Mali fait face à des menaces environnementales croissantes :

| Menace | Impact au Mali | Fréquence |
|--------|---------------|-----------|
| **Sécheresse** | Perte de 20-40% des récoltes par épisode | Tous les 2-3 ans |
| **Feux de brousse** | Destruction de millions d'hectares | Saison sèche (nov-mars) |
| **Inondations** | 300+ morts à Bamako (2024), déplacements massifs | Saison des pluies (juin-oct) |
| **Désertification** | Avancée du Sahara de 1,5 km/an vers le sud | Permanent |
| **Qualité de l'air** | Pollution urbaine croissante (Bamako 3M+ hab.) | Permanent |

**Aujourd'hui, ces données existent mais sont dispersées, techniques et inaccessibles aux décideurs.** ECO-SURVEILLANCE les centralise et les transforme en informations actionnables.

### 1.3 Utilisateurs Cibles

- **Forces de sécurité et défense** : surveillance des zones frontalières et des espaces naturels
- **Gouvernement local** : prévention des catastrophes, planification territoriale
- **ONG environnementales** : suivi des projets de reforestation et de conservation
- **Chercheurs** : accès à des données harmonisées pour l'analyse scientifique
- **Populations locales** : alertes précoces via les canaux de communication existants

### 1.4 Valeur Ajoutée

```
     DONNÉES BRUTES                    ECO-SURVEILLANCE                    DÉCIDEURS
  ┌──────────────────┐            ┌──────────────────────┐            ┌──────────────────┐
  │ Fichiers NetCDF  │            │                      │            │ "Risque CRITIQUE │
  │ GeoTIFF (90 Mo)  │ ──collecte─│  Normalisation        │ ──alerte── │  de sécheresse   │
  │ APIs JSON        │            │  Calcul d'indices     │            │  dans votre zone"│
  │ CSV (FIRMS)      │            │  Détection d'anomalies│            │                  │
  │ OData (Copernicus│            │  Évaluation de risques│            │ Dashboard web    │
  └──────────────────┘            │  IA explicative       │            │ API pour systèmes│
                                  └──────────────────────┘            └──────────────────┘
                                        │
                                   4 moteurs
                                   9 tâches auto
                                   7 providers
                                   13 endpoints
```

---

## 2. Architecture Technique

### 2.1 Stack Technologique

| Composant | Technologie | Rôle |
|-----------|------------|------|
| Backend | Django 4.2 + Django ORM | Framework web, logique métier, API |
| Base de données | SQLite (dev) / PostgreSQL+PostGIS (prod) | Stockage persistant |
| Cache | Redis | Cache des résultats, sessions |
| Tâches asynchrones | Celery + Redis | Synchronisation automatique des données |
| Frontend | Django Templates + Tailwind CSS CDN | Interface responsive |
| Cartographie | Leaflet.js | Visualisation cartographique interactive |
| Graphiques | Chart.js | Tableaux de bord visuels |
| Intelligence artificielle | Groq API (Llama 3.3 70B) | Analyse et recommandations |

### 2.2 Pipeline de Traitement

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           PIPELINE COMPLET                                  │
│                                                                             │
│  ┌─────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐  │
│  │ COLLECTE│──▶│NORMALISA-│──▶│  INDICES │──▶│ ANOMALIES│──▶│  RISQUES │  │
│  │         │   │   TION   │   │          │   │          │   │          │  │
│  │ 7 sources│   │ Format   │   │ NDVI     │   │ Z-score  │   │ 7 profils│  │
│  │ réelles │   │ standard │   │ NDWI     │   │ Baselines│   │ Pondérés │  │
│  └─────────┘   └──────────┘   │ NBR      │   │ Seuils   │   └─────┬────┘  │
│                               │ NDMI     │   └──────────┘         │      │
│                               └──────────┘                        ▼      │
│                                                                ┌──────┐  │
│                                     ┌──────────┐   ┌────────┐  │ IEZ  │  │
│                                     │  IA      │◀──│ALERTES │  │      │  │
│                                     │Groq/Llama│   │ 7 règles│  │Score │  │
│                                     │Recommand.│   │Auto    │  │0-100 │  │
│                                     └──────────┘   └────────┘  └──┬───┘  │
│                                                                   │      │
│                                                                ┌──▼───┐  │
│                                                                │DASH- │  │
│                                                                │BOARD │  │
│                                                                └──────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 2.3 Modèle de Données

```
MonitoringZone (zone géographique)
    ├── FireDetection (incendies FIRMS)
    ├── VegetationObservation (NDVI, NDWI, NBR, NDMI — Sentinel-2, Landsat)
    ├── ClimateObservation (température, pluie, humidité — NASA POWER)
    ├── AtmosphericObservation (SO2, O3, NO2, AER_AI — Sentinel-5P)
    ├── WaterObservation (niveaux d'eau)
    ├── SatelliteObservation (méta-informations satellite)
    ├── MonitoringStation (capteurs IoT)
    ├── Sensor (capteurs individuels)
    ├── Anomaly (anomalies détectées)
    ├── RiskAssessment (évaluations de risque)
    └── Incident (incidents environnementaux)
```

---

## 3. Sources de Données

### 3.1 Vue d'ensemble

| # | Source | Fournisseur | Type | Couverture | Mode d'accès | Statut |
|---|--------|------------|------|-----------|--------------|--------|
| 1 | **FIRMS** | NASA | Feux de brousse | Mondial | API REST (clé API) | Réel |
| 2 | **NASA POWER** | NASA | Données climatiques | Mondial | API REST (gratuit) | Réel |
| 3 | **Sentinel-2** | ESA/Copernicus | Végétation (NDVI) | Mali/UEMOA | STAC (OAuth2) | Réel |
| 4 | **Sentinel-5P** | ESA/Copernicus | Atmosphère (SO2, O3) | Mali/UEMOA | OData (OAuth2) | Réel |
| 5 | **Landsat** | USGS/NASA | Imagerie terrestre | Mondial | STAC Planetary Computer (gratuit) | Réel |
| 6 | **OpenAQ** | OpenAQ Foundation | Qualité de l'air | Partiel | API REST v3 (clé API) | Réel |
| 7 | **Groq AI** | Groq Inc. | Analyse et IA | Mondial | API REST (clé API) | Réel |

### 3.2 Détails par Source

#### 3.2.1 FIRMS — Fire Information for Resource Management System
- **Données** : Détection de feux actifs (points chauds) via satellites MODIS et VIIRS
- **Fréquence** : Toutes les 3-6 heures (NRT — Near Real Time)
- **Résolution** : 375m (VIIRS) / 1km (MODIS)
- **Utilisation** : Calcul de densité de feux par zone, tendances saisonnières
- **Format de sortie** : Coordonnées GPS, intensité radiante, date de détection

#### 3.2.2 NASA POWER — Prediction of Worldwide Energy Resources
- **Données** : Variables climatiques (température, précipitations, humidité, vent, rayonnement solaire)
- **Fréquence** : Quotidienne (avec retard de ~2 jours)
- **Résolution** : 0.5° × 0.5° (~50km)
- **Variables** : T2M (temp), PRECTOT (pluie), RH2M (humidité), WS2M (vent), ALLSKY_SFC_SW_DWN (solaire), T2M_MAX/MIN
- **Utilisation** : Calcul de l'indice IEZ, corrélation végétation-climat

#### 3.2.3 Sentinel-2 — Imagerie multispectrale
- **Données** : Images multispectrales (13 bandes, 10-60m de résolution)
- **Fréquence** : Tous les 5 jours
- **Bandes clés** : B04 (Rouge, 665nm), B08 (NIR, 842nm), B11 (SWIR, 1610nm)
- **Indices calculés** : NDVI, NDWI, NBR, NDMI
- **Qualité** : Filtrage automatique par couverture nuageuse

#### 3.2.4 Sentinel-5P — Surveillance atmosphérique
- **Données** : Gaz trace et aérosols atmosphériques
- **Fréquence** : Quotidienne
- **Variables** : SO2, O3, NO2, AER_AI (Indice d'Aérosol), CO, CH4, HCHO
- **Utilisation** : Qualité de l'air, détection de pollution industrielle/volcanique

#### 3.2.5 Landsat Collection 2 Level-2
- **Données** : Imagerie haute résolution (30m, 9 bandes spectrales)
- **Fréquence** : Tous les 16 jours (Landsat 8+9 combinés)
- **Accès** : Microsoft Planetary Computer (STAC, gratuit, sans clé API)
- **Bandes** : SR_B4 (Rouge), SR_B5 (NIR), SR_B3 (Vert), SR_B6/B7 (SWIR)
- **Indices** : NDVI, NDWI, NBR, NDMI (complément à Sentinel-2)

#### 3.2.6 OpenAQ — Qualité de l'air
- **Données** : Mesures de qualité de l'air au sol (PM2.5, PM10, O3, NO2, SO2, CO)
- **Couverture** : ~300 stations en Afrique (partielle au Mali)
- **API** : Version 3 avec géolocalisation
- **Utilisation** : Corrélation avec les données satellitaires Sentinel-5P

#### 3.2.7 Groq AI — Intelligence Artificielle
- **Modèle** : Llama 3.3 70B via Groq (latence < 1s)
- **Utilisation** : Interprétation des incidents, recommandations contextuelles
- **Limites** : Ne prend pas de décision — explique, contextualise, recommande

---

## 4. Moteurs d'Analyse

### 4.1 RiskEngine — Moteur de Risque

Calcule un score de risque (0-100) pour chaque zone de surveillance, basé sur 7 profils pondérés :

| Profil | Composants | Pondération |
|--------|-----------|-------------|
| **Feu de forêt** | NDVI, température, humidité, feux FIRMS | 25% |
| **Sécheresse** | NDVI, pluie, humidité, température | 20% |
| **Inondation** | Pluie, NDWI, topographie | 15% |
| **Érosion** | NDVI, pente, NDWI | 10% |
| **Pollution** | SO2, NO2, AER_AI | 10% |
| **Désertification** | NDVI tendance, pluie, température | 10% |
| **Biodiversité** | NDVI, superficie verte | 10% |

**Niveaux de risque** :
- `0-20` : FAIBLE (vert)
- `21-40` : MODÉRÉ (jaune)
- `41-60` : ÉLEVÉ (orange)
- `61-80` : CRITIQUE (rouge)
- `81-100` : EXTRÊME (rouge foncé)

### 4.2 AnomalyEngine — Détection d'Anomalies

Détecte automatiquement les valeurs aberrantes par rapport aux baselines historiques :

```
Pour chaque métrique :
    Z-score = (valeur_actuelle - moyenne_historique) / écart_type

    Si |Z-score| > 2  → Anomalie détectée
    Si |Z-score| > 3  → Anomalie critique
```

**Métriques surveillées** : NDVI, NDWI, température, pluie, SO2, O3

### 4.3 IEZEngine — Indice d'Éco-Zone

Score composite (0-100) de santé globale de l'écosystème, calculé à partir de 7 composantes pondérées :

| Composante | Pondération | Source |
|-----------|-------------|--------|
| Couverture végétale (NDVI) | 25% | Sentinel-2 / Landsat |
| Disponibilité hydrique (NDWI) | 20% | Sentinel-2 |
| Stabilité climatique | 15% | NASA POWER |
| Qualité de l'air | 15% | Sentinel-5P / OpenAQ |
| Absence de feux | 15% | FIRMS |
| Biodiversité (proxy) | 5% | Sentinel-2 |
| Pression anthropique | 5% | Détection d'anomalies |

### 4.4 AlertEngine — Moteur d'Alertes

**7 règles d'alerte automatiques** :

| Règle | Condition | Niveau |
|-------|-----------|--------|
| Alerte feu | Feu FIRMS actif dans la zone | CRITIQUE |
| Alerte sécheresse | NDVI < baseline - 2σ ET pluie < 50% normale | ÉLEVÉ |
| Alerte inondation | NDWI > 0.4 ET pluie > 100mm/3j | ÉLEVÉ |
| Alerte pollution | SO2 > 0.5 DU OU NO2 > 50 µg/m³ | MODÉRÉ |
| Alerte érosion | NDVI en baisse > 15% sur 30 jours | MODÉRÉ |
| Alerte désertification | NDVI < 0.15 pendant > 60 jours | ÉLEVÉ |
| Alerte anomaly | Z-score > 3 sur n'importe quelle métrique | MODÉRÉ |

---

## 5. Interface Utilisateur — Dashboard

### 5.1 Tableau de Bord Principal

Le dashboard affiche en temps réel :

- **Carte interactive** (Leaflet) avec tous les points de surveillance
- **Scores de risque** par zone (codes couleur)
- **Graphiques** d'évolution des indices NDVI, NDWI, température
- **Alertes actives** triées par priorité
- **Statistiques globales** : nombre de zones, feux actifs, risque moyen

### 5.2 Navigation

```
┌──────────────────────────────────────────────────────────┐
│  ECO-SURVEILLANCE MALI          [Dashboard] [Carte] [API]│
├──────────────────────────────────────────────────────────┤
│                                                          │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌─────────┐ │
│  │ Feux     │  │ Végétat° │  │ Climat   │  │Qualité  │ │
│  │ (FIRMS)  │  │ (NDVI)   │  │ (POWER)  │  │ air     │ │
│  └──────────┘  └──────────┘  └──────────┘  └─────────┘ │
│                                                          │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌─────────┐ │
│  │Risques   │  │ Anomalies│  │ Satellit │  │Incidents│ │
│  │ (auto)   │  │ (auto)   │  │ (S2/L8)  │  │(alertes)│ │
│  └──────────┘  └──────────┘  └──────────┘  └─────────┘ │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

---

## 6. API REST — Guide Complet

### 6.1 Endpoints Disponibles

L'API est accessible via HTTP sur le port configuré (défaut : 8000).

| Méthode | Endpoint | Description | Données retournées |
|---------|----------|-------------|-------------------|
| GET | `/api/dashboard/` | Tableau de bord global | Zones, alertes, risque moyen |
| GET | `/api/map/` | Données cartographiques | Géométries, scores, feux |
| GET | `/api/vegetation/` | Indices de végétation | NDVI, NDWI, NBR, NDMI par zone |
| GET | `/api/climate/` | Données climatiques | Temp, pluie, humidité, vent |
| GET | `/api/iez/` | Indice d'Éco-Zone | Score IEZ par zone |
| GET | `/api/air-quality/` | Qualité de l'air | SO2, O3, NO2, AER_AI |
| GET | `/api/risk/` | Évaluations de risque | Score et niveau par zone |
| GET | `/api/satellite/` | Observations satellite | Méta-informations Sentinel/Landsat |
| GET | `/api/zones/` | Zones de surveillance | Liste des zones avec coordonnées |
| GET | `/api/fires/` | Détections de feux | Points chauds FIRMS |
| GET | `/api/stations/` | Stations de surveillance | Capteurs et stations |
| GET | `/api/incidents/` | Incidents | Incidents enregistrés |
| GET | `/api/alertes/` | Alertes actives | Alertes par niveau et type |
| POST | `/incidents/{id}/analyze/` | Analyse IA d'un incident | Recommandations Groq AI |

### 6.2 Exemples d'Utilisation

#### Récupérer les alertes actives
```bash
curl -X GET http://localhost:8000/api/alertes/
```

**Réponse** :
```json
[
  {
    "id": 1,
    "zone": "Bamako Nord",
    "type": "FEU",
    "niveau": "CRITIQUE",
    "message": "Feu actif détecté à 12.65°N, -8.01°E",
    "created_at": "2026-08-19T14:30:00Z"
  }
]
```

#### Récupérer le risque par zone
```bash
curl -X GET http://localhost:8000/api/risk/
```

**Réponse** :
```json
[
  {
    "zone": "Bamako",
    "score": 45,
    "niveau": "ÉLEVÉ",
    "profile": "FEU_FORET",
    "details": {
      "ndvi": 0.32,
      "temperature": 38.5,
      "feux_proches": 3
    }
  }
]
```

#### Analyser un incident avec l'IA
```bash
curl -X POST http://localhost:8000/incidents/1/analyze/
```

**Réponse** :
```json
{
  "success": true,
  "summary": "Incident de type feu de forêt détecté dans la zone de Bamako. Le NDVI montre une baisse significative (-0.15) sur les 30 derniers jours. Trois points actifs FIRMS sont identifiés dans un rayon de 5km. Recommandation : déploiement rapide d'équipe d'intervention, surveillance accrue des zones adjacentes.",
  "model": "groq/compound"
}
```

---

## 7. Tâches Automatisées

Le système exécute automatiquement 9 tâches via Celery + Redis :

| Tâche | Fréquence | Description |
|-------|-----------|-------------|
| `sync-firms` | Toutes les 6h | Synchronisation des feux FIRMS |
| `sync-nasa-power` | Toutes les 6h | Synchronisation données climatiques |
| `sync-sentinel2-vegetation` | Toutes les 12h | Calcul NDVI/NDWI/NBR/NDMI |
| `sync-sentinel5p-atmospheric` | Toutes les 6h | Collecte SO2/O3/NO2 |
| `compute-all-risks` | Toutes les 6h | Recalcul des scores de risque |
| `compute-iez` | Toutes les 6h | Recalcul des indices IEZ |
| `detect-anomalies` | Toutes les 6h | Détection d'anomalies |
| `evaluate-alerts` | Toutes les 3h | Évaluation des règles d'alerte |
| `simulate-sensors` | Toutes les 1h | Simulation des capteurs IoT (MVP) |

---

## 8. Guide d'Installation

### 8.1 Prérequis

```bash
# Python 3.12+
python3 --version

# Redis (pour Celery)
redis-cli ping

# Git
git --version
```

### 8.2 Installation

```bash
# 1. Cloner le dépôt
git clone <url-du-depot>
cd ECO-SURVEILLANCE

# 2. Créer l'environnement virtuel
python3 -m venv ../env
source ../env/bin/activate

# 3. Installer les dépendances
pip install -r requirements.txt

# 4. Configurer les variables d'environnement
cp .env.example .env
# Éditer .env avec vos clés API

# 5. Initialiser la base de données
python manage.py migrate

# 6. Créer un superutilisateur
python manage.py createsuperuser

# 7. Lancer le serveur
python manage.py runserver

# 8. (Optionnel) Lancer Celery pour les tâches automatiques
celery -A config worker -l info &
celery -A config beat -l info &
```

### 8.3 Vérification

```bash
# Vérifier que le serveur fonctionne
curl http://localhost:8000/api/dashboard/

# Vérifier les endpoints
curl http://localhost:8000/api/vegetation/
curl http://localhost:8000/api/risk/
curl http://localhost:8000/api/air-quality/
```

---

## 9. Configuration

### 9.1 Variables d'Environnement (.env)

```bash
# === MODE ===
DEMO_MODE=0              # 0=données réelles, 1=mode simulation

# === DJANGO ===
SECRET_KEY=<clé-secrète>
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# === BASE DE DONNÉES ===
DATABASE_URL=sqlite:///db.sqlite3

# === REDIS ===
REDIS_URL=redis://localhost:6379/0

# === CLÉS API (obligatoires) ===
FIRMS_API_KEY=<votre-clé-nasa-firms>
CDSE_CLIENT_ID=<votre-client-id-copernicus>
CDSE_CLIENT_SECRET=<votre-client-secret-copernicus>
OPENAQ_API_KEY=<votre-clé-openaq>
GROQ_API_KEY=<votre-clé-groq>

# === CLÉS API (optionnelles) ===
AWS_ACCESS_KEY_ID=<votre-access-key-aws>
AWS_SECRET_ACCESS_KEY=<votre-secret-key-aws>
AWS_REGION=us-east-1

# === CONFIGURATION IA ===
GROQ_MODEL=groq/compound  # Modèle Groq à utiliser
```

### 9.2 Configuration des Fournisseurs

Chaque provider peut être configuré indépendamment via les paramètres Django :

```python
# config/settings.py
CDSE_CLIENT_ID = config("CDSE_CLIENT_ID", default="")
CDSE_CLIENT_SECRET = config("CDSE_CLIENT_SECRET", default="")
FIRMS_API_KEY = config("FIRMS_API_KEY", default="")
NASA_POWER_BASE_URL = "https://power.larc.nasa.gov/api/temporal"
OPENAQ_API_KEY = config("OPENAQ_API_KEY", default="")
```

---

## 10. Glossaire

| Terme | Définition |
|-------|-----------|
| **NDVI** | Normalized Difference Vegetation Index — Indice de végétation (-1 à 1). > 0.3 = végétation saine |
| **NDWI** | Normalized Difference Water Index — Indice d'eau (> 0 = présence d'eau) |
| **NBR** | Normalized Burn Ratio — Indice de brûlure (post-feu) |
| **NDMI** | Normalized Difference Moisture Index — Indice d'humidité foliaire |
| **IEZ** | Indice d'Éco-Zone — Score composite de santé écologique (0-100) |
| **STAC** | SpatioTemporal Asset Catalog — Standard d'indexation de données géospatiales |
| **CDSE** | Copernicus Data Space Ecosystem — Plateforme d'accès aux données Sentinel |
| **FIRMS** | Fire Information for Resource Management System — Système de détection de feux NASA |
| **AER_AI** | Absorbing Aerosol Index — Indice d'aérosols absorbants |
| **NRT** | Near Real Time — Proche temps réel (retard de quelques heures) |
| **Requester Pays** | Modèle où le demandeur paie les coûts de transfert de données (AWS S3) |
| **Celery** | Framework de tâches asynchrones pour Python |
| **GeoTIFF** | Format d'image géoréférencée utilisé par les satellites |

---

## Informations de Contact

**Projet ECO-SURVEILLANCE MALI**
- Auteur : M. Kane
- Date : Août 2026
- Version : 1.0
- Licence : Projet académique

---

*Document généré automatiquement — Dernière mise à jour : 19 août 2026*
