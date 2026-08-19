"""
Copernicus Sentinel-2 L2A provider.
Fetches multispectral satellite imagery and computes vegetation/water indices.
Uses Copernicus Data Space Ecosystem (CDSE) STAC + Process API.
Auth: OAuth2 client credentials.
"""
import logging
import os
import math
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from django.utils import timezone
from .base import BaseDataProvider, DataSourceResult, ProviderHealth

logger = logging.getLogger("data_providers.sentinel2")


class Sentinel2Provider(BaseDataProvider):
    name = "Sentinel-2"
    source_type = "SATELLITE"
    is_optional = False

    # Copernicus Data Space Ecosystem
    STAC_URL = "https://stac.dataspace.copernicus.eu/v1"
    PROCESS_URL = "https://sh.dataspace.copernicus.eu/process/v1"
    TOKEN_URL = "https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/token"

    # Sentinel-2 L2A collection
    COLLECTION = "sentinel-2-l2a"
    PRODUCT_TYPE = "S2MSI2A"  # L2A (atmospherically corrected)

    # Key bands for MVP indices
    BANDS = {
        "B03": "GREEN",   # 10m, 560nm
        "B04": "RED",     # 10m, 665nm
        "B08": "NIR",     # 10m, 842nm
        "B11": "SWIR1",   # 20m, 1610nm
        "B12": "SWIR2",   # 20m, 2190nm
    }

    # Indices that can be computed
    INDICES = {
        "NDVI": {"formula": "(B08 - B04) / (B08 + B04)", "bands": ["B04", "B08"], "range": (-1, 1)},
        "NDWI": {"formula": "(B03 - B08) / (B03 + B08)", "bands": ["B03", "B08"], "range": (-1, 1)},
        "NBR": {"formula": "(B08 - B12) / (B08 + B12)", "bands": ["B08", "B12"], "range": (-1, 1)},
        "NDMI": {"formula": "(B08 - B11) / (B08 + B11)", "bands": ["B08", "B11"], "range": (-1, 1)},
    }

    def __init__(self, client_id: str = "", client_secret: str = "", **kwargs):
        super().__init__(**kwargs)
        self.client_id = client_id
        self.client_secret = client_secret
        self._token = None
        self._token_expiry = None
        import requests
        self.session = requests.Session()

    def health_check(self) -> ProviderHealth:
        if not self.client_id or not self.client_secret:
            return ProviderHealth(
                status="not_configured",
                reason="CDSE_CLIENT_ID / CDSE_CLIENT_SECRET manquants"
            )
        try:
            token = self._get_token()
            if token:
                return ProviderHealth(status="ok")
            return ProviderHealth(status="error", reason="Échec authentification CDSE")
        except Exception as e:
            return ProviderHealth(status="error", reason=str(e))

    def _get_token(self) -> Optional[str]:
        """Get OAuth2 token from CDSE."""
        import time
        if self._token and self._token_expiry and time.time() < self._token_expiry:
            return self._token

        try:
            resp = self.session.post(
                self.TOKEN_URL,
                data={
                    "grant_type": "client_credentials",
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                },
                timeout=30,
            )
            resp.raise_for_status()
            data = resp.json()
            self._token = data.get("access_token")
            expires_in = data.get("expires_in", 600)
            self._token_expiry = time.time() + expires_in - 60  # refresh 60s early
            return self._token
        except Exception as e:
            logger.error("CDSE token error: %s", str(e))
            return None

    def search(self, aoi: Dict = None, start_date: str = None, end_date: str = None,
               max_cloud_cover: float = 30, **kwargs) -> List[Dict[str, Any]]:
        """
        Search for Sentinel-2 L2A products via STAC.
        aoi: {"west": lon, "south": lat, "east": lon, "north": lat} or bbox [w, s, e, n]
        """
        if not start_date:
            end_date = end_date or datetime.now().strftime("%Y-%m-%d")
            start_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
        if not end_date:
            end_date = datetime.now().strftime("%Y-%m-%d")

        # Build STAC search body
        if aoi:
            if isinstance(aoi, dict):
                bbox = [aoi.get("west", -10), aoi.get("south", 10),
                        aoi.get("east", 0), aoi.get("north", 20)]
            else:
                bbox = aoi
        else:
            # Default Mali bbox
            bbox = [-12.0, 10.0, 4.0, 25.0]

        body = {
            "collections": [self.COLLECTION],
            "bbox": bbox,
            "datetime": f"{start_date}T00:00:00Z/{end_date}T23:59:59Z",
            "limit": 20,
        }

        # Apply cloud cover filter via query params (post-filter in code)
        try:
            token = self._get_token()
            headers = {"Authorization": f"Bearer {token}"} if token else {}
            resp = self.session.post(
                f"{self.STAC_URL}/search",
                json=body,
                headers=headers,
                timeout=30,
            )
            resp.raise_for_status()
            data = resp.json()
            features = data.get("features", [])

            # Filter by cloud cover client-side
            filtered = []
            for f in features:
                props = f.get("properties", {})
                cloud_cover = props.get("eo:cloud_cover", 100)
                if cloud_cover <= max_cloud_cover:
                    filtered.append({
                        "id": f["id"],
                        "geometry": f.get("geometry"),
                        "properties": props,
                        "assets": f.get("assets", {}),
                        "bbox": f.get("bbox"),
                    })

            return filtered
        except Exception as e:
            logger.error("Sentinel-2 STAC search failed: %s", str(e))
            return []

    def fetch(self, aoi: Dict = None, start_date: str = None, end_date: str = None,
              bands: List[str] = None, max_cloud_cover: float = 30, **kwargs) -> List[DataSourceResult]:
        """Search and prepare band assets for download."""
        if bands is None:
            bands = ["B04", "B08"]  # Default: NDVI bands

        products = self.search(aoi=aoi, start_date=start_date, end_date=end_date,
                               max_cloud_cover=max_cloud_cover)
        results = []
        for product in products:
            assets = product.get("assets", {})
            band_assets = {}
            for band in bands:
                # Assets are named like B04_10m, B04_20m, B08_10m, etc.
                asset = assets.get(band, {})
                if not asset:
                    # Try matching by prefix (e.g. B04 -> B04_10m)
                    for key, val in assets.items():
                        if key.startswith(band + "_"):
                            asset = val
                            break
                if asset:
                    band_assets[band] = {
                        "href": asset.get("href"),
                        "type": asset.get("type"),
                    }

            results.append(DataSourceResult(
                source=self.name,
                data={
                    "product_id": product["id"],
                    "bands": band_assets,
                    "geometry": product.get("geometry"),
                    "properties": product.get("properties", {}),
                    "bbox": product.get("bbox"),
                },
                fetched_at=timezone.now(),
                is_simulated=False,
                metadata={
                    "cloud_cover": product.get("properties", {}).get("cloudCover"),
                    "date": product.get("properties", {}).get("datetime"),
                },
            ))
        return results

    def normalize(self, raw_data: Any) -> List[Dict[str, Any]]:
        """
        Process band data and compute indices.
        In real mode: downloads bands, reads rasters, computes NDVI/NDWI/NBR/NDMI.
        In demo mode: returns placeholder values.
        """
        if isinstance(raw_data, DataSourceResult):
            raw_data = raw_data.data

        if not isinstance(raw_data, dict):
            return []

        product_id = raw_data.get("product_id", "")
        properties = raw_data.get("properties", {})
        bands = raw_data.get("bands", {})
        geometry = raw_data.get("geometry")

        # Extract zone coords from geometry
        lat, lng = self._extract_center(geometry)

        records = []

        if self.demo_mode or not bands:
            # Demo mode: generate plausible values
            import random
            for index_name, info in self.INDICES.items():
                val = round(random.uniform(-0.1, 0.8), 4)
                records.append({
                    "index_name": index_name,
                    "value": val,
                    "baseline_value": round(val + random.uniform(-0.1, 0.1), 4),
                    "std_dev": round(random.uniform(0.05, 0.15), 4),
                    "latitude": lat,
                    "longitude": lng,
                    "acquisition_date": properties.get("datetime", timezone.now().date()),
                    "source": self.name,
                    "is_simulated": True,
                    "metadata": {"product_id": product_id, "formula": info["formula"]},
                })
            return records

        # Real mode: compute indices from band data
        try:
            import rasterio
            import numpy as np
            band_data = {}
            for band_name, asset_info in bands.items():
                href = asset_info.get("href")
                if not href:
                    continue
                resp = self.session.get(href, timeout=120)
                resp.raise_for_status()
                import tempfile
                with tempfile.NamedTemporaryFile(suffix=".tif", delete=False) as tmp:
                    tmp.write(resp.content)
                    tmp_path = tmp.name
                with rasterio.open(tmp_path) as src:
                    band_data[band_name] = src.read(1).astype(np.float32)
                    if src.nodata:
                        band_data[band_name][band_data[band_name] == src.nodata] = np.nan
                os.unlink(tmp_path)

            # Compute indices
            for index_name, info in self.INDICES.items():
                required_bands = info["bands"]
                if not all(b in band_data for b in required_bands):
                    continue

                b1 = band_data[required_bands[0]]
                b2 = band_data[required_bands[1]]

                # Handle different resolutions (B11/B12 are 20m, others 10m)
                if b1.shape != b2.shape:
                    from rasterio.enums import Resampling
                    import rasterio
                    # Resample to match
                    scale = b1.shape[0] / b2.shape[0]
                    b2_resized = np.array(
                        __import__('scipy.ndimage', fromlist=['zoom']).zoom(b2, scale)
                    ) if b1.shape[0] > b2.shape[0] else b2
                    if b1.shape != b2_resized.shape:
                        continue
                    b2 = b2_resized

                # Compute index
                with np.errstate(divide='ignore', invalid='ignore'):
                    index = (b2 - b1) / (b2 + b1)
                    index = np.where(np.isfinite(index), index, np.nan)

                valid = index[~np.isnan(index)]
                if len(valid) == 0:
                    continue

                records.append({
                    "index_name": index_name,
                    "value": float(np.mean(valid)),
                    "baseline_value": None,
                    "std_dev": float(np.std(valid)),
                    "latitude": lat,
                    "longitude": lng,
                    "acquisition_date": properties.get("datetime", timezone.now().date()),
                    "source": self.name,
                    "is_simulated": False,
                    "metadata": {
                        "product_id": product_id,
                        "formula": info["formula"],
                        "valid_pixels": int(len(valid)),
                    },
                })
            return records

        except ImportError:
            logger.warning("rasterio not available — falling back to simulated values")
            import random
            for index_name, info in self.INDICES.items():
                val = round(random.uniform(-0.1, 0.8), 4)
                records.append({
                    "index_name": index_name,
                    "value": val,
                    "baseline_value": round(val + random.uniform(-0.1, 0.1), 4),
                    "std_dev": round(random.uniform(0.05, 0.15), 4),
                    "latitude": lat,
                    "longitude": lng,
                    "acquisition_date": properties.get("datetime", timezone.now().date()),
                    "source": self.name,
                    "is_simulated": True,
                    "metadata": {"product_id": product_id, "formula": info["formula"]},
                })
            return records
        except Exception as e:
            logger.error("Sentinel-2 normalization failed: %s", str(e))
            return []

    def save(self, normalized_data: List[Dict[str, Any]]) -> int:
        """Save vegetation index observations to database."""
        from apps.vegetation.models import VegetationObservation
        from apps.geography.models import MonitoringZone

        saved = 0
        for record in normalized_data:
            try:
                zone = self._find_nearest_zone(record["latitude"], record["longitude"])
                if not zone:
                    continue

                acq_date = record.get("acquisition_date")
                if isinstance(acq_date, str):
                    try:
                        acq_date = datetime.strptime(acq_date[:10], "%Y-%m-%d").date()
                    except ValueError:
                        acq_date = timezone.now().date()
                elif isinstance(acq_date, datetime):
                    acq_date = acq_date.date()

                if VegetationObservation.objects.filter(
                    zone=zone, index_name=record["index_name"],
                    acquisition_date=acq_date
                ).exists():
                    continue

                obs = VegetationObservation(
                    zone=zone,
                    index_name=record["index_name"],
                    value=record["value"],
                    baseline_value=record.get("baseline_value"),
                    std_dev=record.get("std_dev"),
                    acquisition_date=acq_date,
                    source=record.get("source", self.name),
                    is_simulated=record.get("is_simulated", False),
                    metadata=record.get("metadata", {}),
                )
                obs.save()
                saved += 1
            except Exception as e:
                logger.warning("Failed to save vegetation observation: %s", str(e))
        return saved

    def _find_nearest_zone(self, lat: float, lng: float):
        """Find nearest MonitoringZone within 100km."""
        from apps.geography.models import MonitoringZone
        zones = MonitoringZone.objects.exclude(latitude__isnull=True).exclude(longitude__isnull=True)
        best_zone = None
        best_dist = float("inf")
        for zone in zones:
            dlat = math.radians(zone.latitude - lat)
            dlng = math.radians(zone.longitude - lng)
            a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat)) * math.cos(math.radians(zone.latitude)) * math.sin(dlng / 2) ** 2
            dist = 2 * 6371 * math.asin(math.sqrt(a))
            if dist < best_dist:
                best_dist = dist
                best_zone = zone
        if best_zone and best_dist <= 100:
            return best_zone
        return None

    @staticmethod
    def _extract_center(geometry) -> tuple:
        """Extract center coordinates from GeoJSON geometry."""
        if not geometry:
            return 12.6392, -8.0029  # Default Bamako
        geom_type = geometry.get("type", "")
        coords = geometry.get("coordinates", [])
        if geom_type == "Point" and len(coords) >= 2:
            return coords[1], coords[0]  # lat, lng
        elif geom_type in ("Polygon", "MultiPolygon") and coords:
            # Approximate center
            if geom_type == "Polygon":
                ring = coords[0]
            else:
                ring = coords[0][0] if coords[0] else [[0, 0]]
            lats = [c[1] for c in ring]
            lngs = [c[0] for c in ring]
            return sum(lats) / len(lats), sum(lngs) / len(lngs)
        return 12.6392, -8.0029

    def generate_demo_data(self, zones=None) -> int:
        """Generate simulated Sentinel-2 index data."""
        import random
        from apps.vegetation.models import VegetationObservation
        from apps.geography.models import MonitoringZone

        if zones is None:
            zones = list(MonitoringZone.objects.all())
        if not zones:
            return 0

        now = timezone.now()
        observations = []
        for zone in zones:
            for d in range(0, 30, 5):  # Every 5 days
                acq_date = (now - timedelta(days=d)).date()
                for index_name in ["NDVI", "NDWI", "NBR", "NDMI"]:
                    val = round(random.uniform(-0.1, 0.8), 4)
                    observations.append(VegetationObservation(
                        zone=zone, index_name=index_name,
                        value=val,
                        baseline_value=round(val + random.uniform(-0.1, 0.1), 4),
                        std_dev=round(random.uniform(0.05, 0.15), 4),
                        acquisition_date=acq_date,
                        source="Sentinel-2 (simulé)", is_simulated=True,
                    ))
        VegetationObservation.objects.bulk_create(observations, ignore_conflicts=True)
        return len(observations)
