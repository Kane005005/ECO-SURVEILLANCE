# Documentation du Provider Sentinel-5P

## Vue d'ensemble

Le provider Sentinel-5P (`data_providers/sentinel5p.py`) récupère les données atmosphériques (SO2, O3, NO2, aérosols) via les produits Sentinel-5P.

## Sources de données

- **STAC API** : Recherche de produits Sentinel-5P via Copernicus Data Space Ecosystem (CDSE)
- **Process API** : Extraction des données atmosphériques
- **OAuth2** : Authentification via `CDSE_CLIENT_ID` / `CDSE_CLIENT_SECRET`

## Variables atmosphériques

| Variable | Unité | Description | Seuils d'alerte |
|----------|-------|-------------|-----------------|
| **SO2** | DU (Dobson Units) | Dioxyde de soufre | > 10 DU : élevé |
| **O3** | DU | Ozone troposphérique | > 100 DU : anormal |
| **NO2** | DU | Dioxyde d'azote | > 20 DU : élevé |
| **AER_AI** | Index | Indice d'aérosols UV | > 2 : aérosols élevés |
| **CO** | DU | Monoxyde de carbone | > 0.1 DU : pollution |
| **CH4** | DU | Méthane | > 1800 DU : élevé |
| **HCHO** | DU | Formaldéhyde | > 1 DU : pollution |

## Flux de traitement

```
1. search()     → Recherche produits STAC avec filtres (date, variable, zone)
2. fetch()      → Téléchargement des données via Process API
3. normalize()  → Conversion en AtmosphericObservation
4. validate()   → Filtrage des valeurs aberrantes
5. save()       → Sauvegarde en base
```

## Configuration

### Variables d'environnement

```bash
CDSE_CLIENT_ID=your_client_id
CDSE_CLIENT_SECRET=your_client_secret
```

### Endpoints

- **STAC Search** : `https://planetarycomputer.microsoft.com/api/stac/v1/search`
- **Process API** : `https://sh.dataspace.copernicus.eu/api/v1/process`

## Exemple d'utilisation

```python
from data_providers.sentinel5p import Sentinel5PProvider

provider = Sentinel5PProvider()

# Recherche SO2
results = provider.search(
    geometry={"type": "Point", "coordinates": [-3.0, 17.5]},
    date_range=("2024-01-01", "2024-01-05"),
    variable="SO2"
)

# Traitement complet
fetched = provider.fetch(results)
normalized = provider.normalize(fetched, zone_id=1)
validated = provider.validate(normalized)
saved_count = provider.save(validated)
```

## Limitations

- **Résolution temporelle** : Révisite quotidienne
- **Résolution spatiale** : 3.5km x 5.5km (pixels larges)
- **Qualité des données** : Qualité variable selon les conditions atmosphériques
- **Débit API** : Limitations de requêtes

## Démonstration

En mode démo (`DEMO_MODE=1`), le provider génère des données simulées réalistes sans appel API.
