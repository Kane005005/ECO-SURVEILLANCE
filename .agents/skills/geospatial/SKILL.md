# Skill: Geospatial

## Objectif
Implémenter la partie géospatiale avec PostGIS, Leaflet/MapLibre, et traitements spatiaux.

## Conventions
- CRS principal : WGS84 EPSG:4326.
- Toutes les entités métier doivent avoir une géométrie PostGIS.
- Agrégations spatiales via PostGIS, pas côté Python.
- Carte interactive : Leaflet ou MapLibre dans les templates.

## Contraintes
- PostGIS obligatoire.
- Cache des calculs lourds via Celery.
- Earth Engine optionnel et isolé derrière `data_providers/gee.py`.

## Pièges à éviter
- Calculer des agrégations spatiales dans la view.
- Mélanger CRS sans conversion explicite.
- Présenter des indicateurs satellitaires comme mesures locales.

## Fichiers concernés
- `apps/geography/`
- `data_providers/gee.py`
- `templates/...` avec Leaflet/MapLibre
- `static/js/map.js`
