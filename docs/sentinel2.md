# Documentation du Provider Sentinel-2

## Vue d'ensemble

Le provider Sentinel-2 (`data_providers/sentinel2.py`) récupère les données de végétation via les indices spectralaux calculés à partir des bandes Sentinel-2.

## Sources de données

- **STAC API** : Recherche de produits Sentinel-2 via Copernicus Data Space Ecosystem (CDSE)
- **Process API** : Téléchargement des bandes spectralles
- **OAuth2** : Authentification via `CDSE_CLIENT_ID` / `CDSE_CLIENT_SECRET`

## Indices calculés

| Indice | Formule | Description | Utilisation |
|--------|---------|-------------|-------------|
| **NDVI** | (B08-B04)/(B08+B04) | Indice de Végétation par Différence Normalisée | Santé végétale, couverture |
| **NDWI** | (B03-B08)/(B03+B08) | Indice d'Eau par Différence Normalisée | Stress hydrique |
| **NBR** | (B08-B12)/(B08+B12) | Ratio Brûlure Normalisé | Dégâts incendie |
| **NDMI** | (B08-B11)/(B08+B11) | Indice d'Humidité par Différence Normalisée | Humidité végétale |

## Bandes Sentinel-2

| Bande | Longueur d'onde | Résolution | Utilisation |
|-------|----------------|------------|-------------|
| B03 | 560 nm (Vert) | 10m | NDWI |
| B04 | 665 nm (Rouge) | 10m | NDVI |
| B08 | 842 nm (NIR) | 10m | NDVI, NBR, NDMI |
| B11 | 1610 nm (SWIR) | 20m | NDMI |
| B12 | 2190 nm (SWIR) | 20m | NBR |

## Configuration

### Variables d'environnement

```bash
CDSE_CLIENT_ID=your_client_id
CDSE_CLIENT_SECRET=your_client_secret
```

### Endpoints

- **STAC Search** : `https://planetarycomputer.microsoft.com/api/stac/v1/search`
- **Process API** : `https://sh.dataspace.copernicus.eu/api/v1/process`

## Flux de traitement

```
1. search()     → Recherche produits STAC avec filtres (date, cloud cover, zone)
2. fetch()      → Téléchargement des bandes via Process API
3. normalize()  → Calcul des indices (NDVI, NDWI, NBR, NDMI)
4. validate()   → Filtrage des valeurs aberrantes
5. save()       → Sauvegarde en base (VegetationObservation)
```

## Exemple d'utilisation

```python
from data_providers.sentinel2 import Sentinel2Provider

provider = Sentinel2Provider()

# Recherche
results = provider.search(
    geometry={"type": "Point", "coordinates": [-3.0, 17.5]},
    date_range=("2024-01-01", "2024-01-31"),
    max_cloud_cover=30
)

# Traitement complet
fetched = provider.fetch(results)
normalized = provider.normalize(fetched, zone_id=1)
validated = provider.validate(normalized)
saved_count = provider.save(validated)
```

## Limitations

- **Couverture nuageuse** : Les données Sentinel-2 sont affectées par les nuages (filtrage < 30%)
- **Résolution temporelle** : Révisite tous les 5 jours
- **Résolution spatiale** : 10m pour les bandes principales
- **Débit API** : Limitations de requêtes par heure

## Démonstration

En mode démo (`DEMO_MODE=1`), le provider génère des données simulées réalistes sans appel API.
