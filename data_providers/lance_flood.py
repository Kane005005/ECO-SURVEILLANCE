"""
NASA LANCE Flood Data Provider (VIIRS NRT 250m Global Flood Product).
Retrieves Near-Real-Time flood observation tiles for Mali:
- h16v07 (Senegal Basin / Western Mali)
- h17v07 (Niger River Basin & Inner Niger Delta / Central-Eastern Mali)
Decodes raster classifications (Class 3: Flooded, Class 2: Permanent Water) and calculates flooded areas in km2.
"""
import os
import io
import logging
import requests
import numpy as np
from PIL import Image
from datetime import datetime, date, timedelta
from typing import Dict, Any, List, Optional
from decouple import config

from data_providers.base import BaseDataProvider, DataSourceResult, ProviderHealth

logger = logging.getLogger("data_providers")


class LANCEFloodProvider(BaseDataProvider):
    name = "NASA LANCE Flood"
    source_type = "WATER"
    is_optional = True

    # Approximate tile bounds [min_lat, min_lon, max_lat, max_lon]
    TILE_BOUNDS = {
        "h16v07": {"min_lat": 10.0, "max_lat": 20.0, "min_lon": -15.0, "max_lon": -5.0, "basin": "Sénégal / Ouest"},
        "h17v07": {"min_lat": 10.0, "max_lat": 20.0, "min_lon": -5.0, "max_lon": 5.0, "basin": "Niger / Delta Intérieur"},
    }

    # Pixel resolution: 250m x 250m = 0.0625 km2 (standard MODIS/VIIRS grid cell ~ 0.05336 km2)
    KM2_PER_PIXEL = 0.05336

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.earthdata_token = kwargs.get("earthdata_token") or config("EARTHDATA_TOKEN", default="")
        self.base_url = kwargs.get("base_url") or config(
            "LANCE_FLOOD_BASE_URL",
            default="https://nrt3.modaps.eosdis.nasa.gov/archive/allData/5200/VCDWD_L3_F2_NRT/Recent",
        )
        self.timeout = kwargs.get("timeout", 25)
        self.session = requests.Session()
        if self.earthdata_token:
            self.session.headers.update({"Authorization": f"Bearer {self.earthdata_token}"})

    def health_check(self) -> ProviderHealth:
        if not self.earthdata_token:
            if self.demo_mode:
                return ProviderHealth(
                    status="ok",
                    reason="Mode démo activé (NASA LANCE Flood simulé)",
                    details={"demo_mode": True},
                )
            return ProviderHealth(
                status="not_configured",
                reason="EARTHDATA_TOKEN non configuré",
                details={"base_url": self.base_url},
            )
        return ProviderHealth(
            status="ok",
            reason="LANCE Flood configuré avec Bearer Token NASA Earthdata",
            details={"base_url": self.base_url},
        )

    def search(self, **kwargs) -> List[Dict[str, Any]]:
        target_date = kwargs.get("date") or datetime.utcnow().strftime("%Y-%m-%d")
        return [
            {
                "tile": tile_name,
                "date": target_date,
                "product": "VCDWD_L3_F2_NRT",
                "resolution": "250m",
                "basin": meta["basin"],
            }
            for tile_name, meta in self.TILE_BOUNDS.items()
        ]

    def _decode_geotiff_raster(self, raw_bytes: bytes, tile_name: str) -> Dict[str, Any]:
        """
        Decodes GeoTIFF raster bytes using Pillow / NumPy.
        Class 3: Observed flood pixel
        Class 2: Permanent water pixel
        """
        img = Image.open(io.BytesIO(raw_bytes))
        arr = np.array(img)

        flood_mask = (arr == 3)
        flood_pixels = int(np.sum(flood_mask))
        flooded_area_km2 = flood_pixels * self.KM2_PER_PIXEL

        # Extract sample centroids of flooded clusters for GeoJSON visualization
        bounds = self.TILE_BOUNDS.get(tile_name, {"min_lat": 10, "max_lat": 20, "min_lon": -10, "max_lon": 0})
        rows, cols = np.where(flood_mask)
        sample_size = min(len(rows), 40)

        features = []
        if sample_size > 0:
            indices = np.linspace(0, len(rows) - 1, sample_size, dtype=int)
            height, width = arr.shape
            for idx in indices:
                r, c = rows[idx], cols[idx]
                lat = bounds["max_lat"] - (r / height) * (bounds["max_lat"] - bounds["min_lat"])
                lon = bounds["min_lon"] + (c / width) * (bounds["max_lon"] - bounds["min_lon"])
                features.append({
                    "type": "Feature",
                    "geometry": {"type": "Point", "coordinates": [round(lon, 4), round(lat, 4)]},
                    "properties": {
                        "class": "Observed Flood",
                        "tile": tile_name,
                        "pixel_area_ha": round(self.KM2_PER_PIXEL * 100, 2),
                    }
                })

        return {
            "flooded_pixels_count": flood_pixels,
            "flooded_area_km2": round(flooded_area_km2, 2),
            "geojson": {"type": "FeatureCollection", "features": features},
        }

    def fetch(self, **kwargs) -> List[DataSourceResult]:
        from apps.geography.models import MonitoringZone

        target_date_str = kwargs.get("date") or datetime.utcnow().strftime("%Y-%m-%d")
        obs_date = datetime.strptime(target_date_str, "%Y-%m-%d").date()

        results = []
        tiles = ["h16v07", "h17v07"]

        for tile in tiles:
            is_live = False
            raster_data = None

            if self.earthdata_token and not self.demo_mode:
                try:
                    # Catalog listing or direct tile file pattern
                    url = f"{self.base_url.rstrip('/')}/VCDWD_L3_F2_NRT.{tile}.tif"
                    resp = self.session.get(url, timeout=self.timeout)
                    if resp.status_code == 200 and len(resp.content) > 1024:
                        raster_data = self._decode_geotiff_raster(resp.content, tile)
                        is_live = True
                except Exception as e:
                    logger.warning("NASA Earthdata LANCE retrieve error for tile %s: %s", tile, str(e))

            if not is_live or not raster_data:
                # High-fidelity realistic simulation
                raster_data = self._generate_simulated_flood(tile, obs_date)

            # Match with closest monitoring zone
            zone = None
            if tile == "h17v07":
                zone = MonitoringZone.objects.filter(name__icontains="Mopti").first() or MonitoringZone.objects.filter(name__icontains="Delta").first()
            else:
                zone = MonitoringZone.objects.filter(name__icontains="Kayes").first() or MonitoringZone.objects.filter(name__icontains="Koulikoro").first()

            data_dict = {
                "tile_name": tile,
                "observation_date": obs_date.isoformat(),
                "flooded_area_km2": raster_data["flooded_area_km2"],
                "flooded_pixels_count": raster_data["flooded_pixels_count"],
                "flood_geojson": raster_data["geojson"],
                "zone_id": zone.id if zone else None,
                "source": "NASA LANCE VIIRS NRT3",
                "is_simulated": not is_live,
            }

            results.append(
                DataSourceResult(
                    source=self.name,
                    data=data_dict,
                    fetched_at=datetime.utcnow(),
                    is_simulated=not is_live,
                )
            )

        return results

    def _generate_simulated_flood(self, tile: str, obs_date: date) -> Dict[str, Any]:
        """Generates realistic flood observation clusters for the Inner Niger Delta and Senegal basins."""
        month = obs_date.month
        # High flood in Delta Intérieur (h17v07) from August to November
        if tile == "h17v07":
            base_area = 185.4 if month in [8, 9, 10, 11] else 38.2
            center_lat, center_lon = 14.85, -4.25
        else:
            base_area = 42.6 if month in [8, 9, 10] else 12.1
            center_lat, center_lon = 14.45, -11.45

        flooded_pixels = int(base_area / self.KM2_PER_PIXEL)
        features = []

        # Generate realistic spatial cluster polygons and points
        num_clusters = 8 if tile == "h17v07" else 4
        for i in range(num_clusters):
            offset_lat = (i * 0.18) - 0.45
            offset_lon = ((i % 3) * 0.15) - 0.25
            c_lat = center_lat + offset_lat
            c_lon = center_lon + offset_lon

            # Polygon representing flooded sector
            poly_coords = [
                [
                    [round(c_lon - 0.04, 4), round(c_lat - 0.03, 4)],
                    [round(c_lon + 0.04, 4), round(c_lat - 0.03, 4)],
                    [round(c_lon + 0.05, 4), round(c_lat + 0.03, 4)],
                    [round(c_lon - 0.03, 4), round(c_lat + 0.04, 4)],
                    [round(c_lon - 0.04, 4), round(c_lat - 0.03, 4)],
                ]
            ]
            features.append({
                "type": "Feature",
                "geometry": {"type": "Polygon", "coordinates": poly_coords},
                "properties": {
                    "cluster_id": f"{tile}_sec_{i+1}",
                    "tile": tile,
                    "area_km2": round(base_area / num_clusters, 2),
                    "area_ha": round((base_area / num_clusters) * 100, 1),
                    "depth_class": "Observed Flood (Class 3)",
                    "basin": self.TILE_BOUNDS.get(tile, {}).get("basin", "Mali"),
                }
            })

        return {
            "flooded_pixels_count": flooded_pixels,
            "flooded_area_km2": round(base_area, 2),
            "geojson": {"type": "FeatureCollection", "features": features},
        }

    def normalize(self, raw_data: Any) -> List[Dict[str, Any]]:
        if isinstance(raw_data, DataSourceResult):
            return [raw_data.data]
        if isinstance(raw_data, list):
            res = []
            for item in raw_data:
                if isinstance(item, DataSourceResult):
                    res.append(item.data)
                elif isinstance(item, dict):
                    res.append(item)
            return res
        if isinstance(raw_data, dict):
            return [raw_data]
        return []

    def save(self, normalized_data: List[Dict[str, Any]]) -> int:
        from apps.water.models import FloodObservation
        from apps.geography.models import MonitoringZone

        saved_count = 0
        for item in normalized_data:
            try:
                obs_date_val = item.get("observation_date")
                if isinstance(obs_date_val, str):
                    obs_date_val = datetime.strptime(obs_date_val, "%Y-%m-%d").date()

                zone = None
                if item.get("zone_id"):
                    zone = MonitoringZone.objects.filter(id=item["zone_id"]).first()

                FloodObservation.objects.update_or_create(
                    tile_name=item.get("tile_name"),
                    observation_date=obs_date_val,
                    defaults={
                        "zone": zone,
                        "flooded_area_km2": item.get("flooded_area_km2", 0.0),
                        "flooded_pixels_count": item.get("flooded_pixels_count", 0),
                        "flood_geojson": item.get("flood_geojson", {}),
                        "source": item.get("source", "NASA LANCE VIIRS"),
                        "is_simulated": item.get("is_simulated", False),
                    }
                )
                saved_count += 1
            except Exception as e:
                logger.error("Error saving FloodObservation: %s", str(e))
        return saved_count
