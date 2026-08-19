# Data Providers — Documentation

## BaseDataProvider

Tous les providers héritent de `BaseDataProvider` et implémentent:
- `health_check()` → vérifie credentials/connectivité
- `search()` → cherche les produits disponibles
- `fetch()` → récupère les données
- `normalize()` → transforme au format standard
- `validate()` → valide avant sauvegarde
- `save()` → persiste en base
- `sync()` → pipeline complet health→search→fetch→normalize→validate→save

## NASA FIRMS

**Source**: https://firms.modaps.eosdis.nasa.gov/api/
**Auth**: API Key (`FIRMS_MAP_KEY`)
**Type**: Feux actifs (MODIS/VIIRS)
**Variables**: latitude, longitude, brightness, confidence, FRP, satellite
**Fréquence**: toutes les 3-6h
**Coût**: gratuit

## NASA POWER

**Source**: https://power.larc.nasa.gov/api
**Auth**: Open access (aucune clé)
**Type**: Données climatiques historiques
**Variables**: T2M, T2M_MAX, T2M_MIN, RH2M, PRECTOTCORR, WS2M, PS, ALLSKY_SFC_SW_DWN
**Fréquence**: quotidienne
**Coût**: gratuit

## CHIRPS

**Source**: https://data.chc.ucsb.edu/products/CHIRPS-2.0/
**Auth**: Open access
**Type**: Précipitations satellite (GeoTIFF)
**Variables**: precipitation (mm)
**Fréquence**: quotidien, 5 jours, mensuel
**Coût**: gratuit
**Note**: nécessite rasterio/GDAL pour lecture rasters

## Sentinel-2 L2A

**Source**: Copernicus Data Space Ecosystem (CDSE)
**Auth**: OAuth2 client credentials (`CDSE_CLIENT_ID`, `CDSE_CLIENT_SECRET`)
**Collection**: SENTINEL-2, produit S2MSI2A
**Bandes**: B03 (GREEN), B04 (RED), B08 (NIR), B11 (SWIR1), B12 (SWIR2)
**Indices**:
- NDVI = (B08 - B04) / (B08 + B04)
- NDWI = (B03 - B08) / (B03 + B08)
- NBR = (B08 - B12) / (B08 + B12)
- NDMI = (B08 - B11) / (B08 + B11)

**Fréquence**: tous les 5 jours
**Coût**: gratuit (quota applicable)

## Sentinel-5P

**Source**: Copernicus Data Space Ecosystem (CDSE)
**Auth**: OAuth2 client credentials
**Produits**: S5P_NRTI_L2__SO2___, S5P_NRTI_L2__O3____, S5P_NRTI_L2__AER_AI, S5P_NRTI_L2__NO2___
**Variables**: SO2 (DU), O3 (DU), AER_AI_340_380, NO2 (mol/m²)
**Fréquence**: quotidienne (NRTI = Near Real Time)
**Coût**: gratuit (quota applicable)

## Landsat Collection 2

**Source**: AWS S3 (`s3://usgs-landsat/`)
**Auth**: AWS CLI configuré + Requester Pays
**Bandes**: SR_B1-B7, ST_B10, QA_PIXEL, QA_AEROSOL
**Type**: Imagerie complémentaire
**Fréquence**: ~16 jours
**Coût**: frais S3 Requester Pays

## Limitations MVP

- Pas de Google Earth Engine
- Pas d'OpenAQ
- Pas d'ERA5
- IoT réel: simulé uniquement
- Raster processing: rasterio requis pour CHIRPS/Sentinel
- Landsat: recherche metadata non implémentée (fichiers S3 uniquement)
