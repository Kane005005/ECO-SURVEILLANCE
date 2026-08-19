"""
Landsat Collection 2 Level-2 provider.
Accesses imagery via Microsoft Planetary Computer STAC (public, no auth needed).
Primary bands: SR_B4 (Red), SR_B5 (NIR) for NDVI computation.
Fallback: S3 Requester Pays or demo mode if STAC unavailable.
"""
import logging
import math
import os
import tempfile
import time
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
from django.utils import timezone
from .base import BaseDataProvider, DataSourceResult, ProviderHealth

logger = logging.getLogger("data_providers.landsat")

# Planetary Computer STAC (public, free, no API key required)
PC_STAC_URL = "https://planetarycomputer.microsoft.com/api/stac/v1"
PC_SIGN_URL = "https://planetarycomputer.microsoft.com/api/sas/v1/sign"

# Asset name mapping: STAC asset key → Landsat band name
STAC_BAND_MAP = {
    "red": "SR_B4",
    "nir08": "SR_B5",
    "green": "SR_B3",
    "blue": "SR_B2",
    "coastal": "SR_B1",
    "swir16": "SR_B6",
    "swir22": "SR_B7",
    "lwir11": "ST_B10",
    "qa_pixel": "QA_PIXEL",
    "qa_radsat": "QA_RADSAT",
    "qa_aerosol": "QA_AEROSOL",
}

# Surface Reflectance scale factor for Collection 2 Level-2
SR_SCALE = 0.0000275
SR_OFFSET = -0.2


class LandsatProvider(BaseDataProvider):
    name = "Landsat"
    source_type = "SATELLITE"
    is_optional = True

    # Index definitions
    INDEX_BANDS = {
        "NDVI": ("SR_B5", "SR_B4"),
        "NDWI": ("SR_B3", "SR_B5"),
        "NBR": ("SR_B5", "SR_B7"),
        "NDMI": ("SR_B5", "SR_B6"),
    }

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        import requests as _requests
        self.session = _requests.Session()
        self._last_sign_time = 0
        self._sign_delay = 0.5

    def health_check(self) -> ProviderHealth:
        """Check if Planetary Computer STAC is accessible."""
        try:
            resp = self.session.get(f"{PC_STAC_URL}/", timeout=15)
            if resp.status_code == 200:
                return ProviderHealth(
                    status="ok",
                    details={"provider": "planetary_computer", "auth_required": False},
                )
            return ProviderHealth(status="degraded", reason=f"STAC returned {resp.status_code}")
        except Exception as e:
            return ProviderHealth(status="error", reason=str(e))

    def search(self, aoi: Dict = None, start_date: str = None, end_date: str = None,
               max_cloud_cover: float = 20, **kwargs) -> List[Dict[str, Any]]:
        """Search for Landsat scenes via Planetary Computer STAC."""
        if not start_date:
            start_date = (datetime.now() - timedelta(days=90)).strftime("%Y-%m-%d")
        if not end_date:
            end_date = datetime.now().strftime("%Y-%m-%d")

        if aoi:
            if isinstance(aoi, dict):
                bbox = [aoi.get("west", -12), aoi.get("south", 10),
                        aoi.get("east", 4), aoi.get("north", 25)]
            else:
                bbox = aoi
        else:
            bbox = [-12.0, 10.0, 4.0, 25.0]

        body = {
            "collections": ["landsat-c2-l2"],
            "bbox": bbox,
            "datetime": f"{start_date}T00:00:00Z/{end_date}T23:59:59Z",
            "limit": 20,
        }

        if max_cloud_cover is not None:
            body["filter-lang"] = "cql2-json"
            body["filter"] = {
                "op": "<=",
                "args": [{"property": "eo:cloud_cover"}, max_cloud_cover],
            }

        try:
            resp = self.session.post(f"{PC_STAC_URL}/search", json=body, timeout=30)
            resp.raise_for_status()
            data = resp.json()
            features = data.get("features", [])
            return [
                {
                    "id": f["id"],
                    "geometry": f.get("geometry"),
                    "properties": f.get("properties", {}),
                    "assets": f.get("assets", {}),
                    "bbox": f.get("bbox"),
                }
                for f in features
            ]
        except Exception as e:
            logger.error("Landsat STAC search failed: %s", str(e))
            return []

    def _sign_url(self, href: str) -> Optional[str]:
        """Sign a Planetary Computer asset URL to get a SAS token."""
        elapsed = time.time() - self._last_sign_time
        if elapsed < self._sign_delay:
            time.sleep(self._sign_delay - elapsed)
        try:
            resp = self.session.get(PC_SIGN_URL, params={"href": href}, timeout=15)
            self._last_sign_time = time.time()
            resp.raise_for_status()
            return resp.json().get("href")
        except Exception as e:
            logger.warning("Failed to sign URL: %s", str(e))
            return None

    def fetch(self, aoi: Dict = None, start_date: str = None, end_date: str = None,
              bands: List[str] = None, max_cloud_cover: float = 20, **kwargs) -> List[DataSourceResult]:
        """Search and download Landsat band data via Planetary Computer."""
        if bands is None:
            bands = ["red", "nir08"]

        products = self.search(aoi=aoi, start_date=start_date, end_date=end_date,
                               max_cloud_cover=max_cloud_cover)
        results = []
        for product in products[:1]:
            assets = product.get("assets", {})
            band_data = {}
            for band_name in bands:
                asset = assets.get(band_name, {})
                if not asset:
                    continue
                href = asset.get("href", "")
                signed = self._sign_url(href)
                if signed:
                    band_data[band_name] = {
                        "href": signed,
                        "original_href": href,
                        "type": asset.get("type", ""),
                    }

            if band_data:
                results.append(DataSourceResult(
                    source=self.name,
                    data={
                        "product_id": product["id"],
                        "bands": band_data,
                        "geometry": product.get("geometry"),
                        "properties": product.get("properties", {}),
                        "bbox": product.get("bbox"),
                        "cloud_cover": product.get("properties", {}).get("eo:cloud_cover", 0),
                    },
                    fetched_at=timezone.now(),
                    is_simulated=False,
                    metadata={
                        "product_id": product["id"],
                        "cloud_cover": product.get("properties", {}).get("eo:cloud_cover", 0),
                        "date": product.get("properties", {}).get("datetime"),
                    },
                ))
        return results

    def _download_band(self, signed_href: str) -> Optional[str]:
        """Download a band GeoTIFF to a temp file. Returns path."""
        try:
            resp = self.session.get(signed_href, timeout=180, stream=True)
            resp.raise_for_status()
            tmp = tempfile.NamedTemporaryFile(suffix=".tif", delete=False)
            for chunk in resp.iter_content(chunk_size=1024 * 1024):
                tmp.write(chunk)
            tmp.close()
            return tmp.name
        except Exception as e:
            logger.error("Band download failed: %s", str(e))
            return None

    def _compute_indices(self, band_files: Dict[str, str],
                         product_props: Dict) -> List[Dict[str, Any]]:
        """Compute vegetation indices from downloaded band files."""
        try:
            import rasterio
            import numpy as np
        except ImportError:
            logger.warning("rasterio not installed — cannot compute Landsat indices")
            return []

        # Extract center coordinates from geometry
        geometry = product_props.get("geometry", {})
        lat, lng = self._extract_center(geometry)

        # Read band data
        band_arrays = {}
        for band_key, tmp_path in band_files.items():
            try:
                with rasterio.open(tmp_path) as src:
                    band_arrays[band_key] = src.read(1).astype(np.float32)
                    if src.nodata:
                        band_arrays[band_key][band_arrays[band_key] == src.nodata] = np.nan
            except Exception as e:
                logger.warning("Failed to read band %s: %s", band_key, str(e))

        records = []
        acq_date = product_props.get("properties", {}).get("datetime", timezone.now())

        for index_name, (nir_key, red_key) in self.INDEX_BANDS.items():
            nir_stac = next((k for k, v in STAC_BAND_MAP.items() if v == nir_key), None)
            red_stac = next((k for k, v in STAC_BAND_MAP.items() if v == red_key), None)

            if nir_stac not in band_arrays or red_stac not in band_arrays:
                continue

            nir = band_arrays[nir_stac]
            red = band_arrays[red_stac]

            # Handle different resolutions
            if nir.shape != red.shape:
                scale = nir.shape[0] / red.shape[0]
                try:
                    from scipy.ndimage import zoom
                    red = zoom(red, scale)
                except ImportError:
                    logger.warning("scipy not available for resampling")
                    if nir.shape != red.shape:
                        continue

            # Apply scale factor (Collection 2 L2 SR)
            nir_sr = nir * SR_SCALE + SR_OFFSET
            red_sr = red * SR_SCALE + SR_OFFSET

            # Compute index
            with np.errstate(divide="ignore", invalid="ignore"):
                if index_name == "NDVI":
                    index = (nir_sr - red_sr) / (nir_sr + red_sr + 1e-10)
                elif index_name == "NDWI":
                    green_stac = next((k for k, v in STAC_BAND_MAP.items() if v == "SR_B3"), None)
                    if green_stac in band_arrays:
                        green_sr = band_arrays[green_stac] * SR_SCALE + SR_OFFSET
                        index = (green_sr - nir_sr) / (green_sr + nir_sr + 1e-10)
                    else:
                        continue
                elif index_name == "NBR":
                    swir_stac = next((k for k, v in STAC_BAND_MAP.items() if v == "SR_B7"), None)
                    if swir_stac in band_arrays:
                        swir_sr = band_arrays[swir_stac] * SR_SCALE + SR_OFFSET
                        index = (nir_sr - swir_sr) / (nir_sr + swir_sr + 1e-10)
                    else:
                        continue
                elif index_name == "NDMI":
                    swir_stac = next((k for k, v in STAC_BAND_MAP.items() if v == "SR_B6"), None)
                    if swir_stac in band_arrays:
                        swir_sr = band_arrays[swir_stac] * SR_SCALE + SR_OFFSET
                        index = (nir_sr - swir_sr) / (nir_sr + swir_sr + 1e-10)
                    else:
                        continue
                else:
                    continue

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
                "acquisition_date": acq_date if isinstance(acq_date, str) else acq_date.date() if hasattr(acq_date, "date") else acq_date,
                "source": self.name,
                "is_simulated": False,
                "metadata": {
                    "product_id": product_props.get("product_id", ""),
                    "bands_used": [nir_key, red_key],
                    "valid_pixels": int(len(valid)),
                    "total_pixels": int(index.size),
                },
            })

        return records

    def _extract_center(self, geometry: Any) -> Tuple[float, float]:
        """Extract center coordinates from GeoJSON geometry."""
        if not geometry:
            return 12.6392, -8.0029
        coords = geometry.get("coordinates", [])
        geom_type = geometry.get("type", "")
        if geom_type == "Point" and len(coords) >= 2:
            return coords[1], coords[0]
        elif geom_type == "Polygon" and coords:
            ring = coords[0]
            if ring:
                lats = [c[1] for c in ring]
                lngs = [c[0] for c in ring]
                return sum(lats) / len(lats), sum(lngs) / len(lngs)
        return 12.6392, -8.0029

    def normalize(self, raw_data: Any) -> List[Dict[str, Any]]:
        """Download bands, compute indices, and return records."""
        if isinstance(raw_data, DataSourceResult):
            raw_data = raw_data.data

        if not isinstance(raw_data, dict):
            return []

        bands_info = raw_data.get("bands", {})
        if not bands_info:
            return []

        # Download bands to temp files
        band_files = {}
        for band_name, info in bands_info.items():
            signed_href = info.get("href", "")
            if not signed_href:
                continue
            tmp_path = self._download_band(signed_href)
            if tmp_path:
                band_files[band_name] = tmp_path

        if not band_files:
            return []

        try:
            records = self._compute_indices(band_files, raw_data)
            return records
        finally:
            # Cleanup temp files
            for tmp_path in band_files.values():
                try:
                    os.unlink(tmp_path)
                except OSError:
                    pass

    def save(self, normalized_data: List[Dict[str, Any]]) -> int:
        """Save Landsat observations to VegetationObservation + SatelliteObservation."""
        from apps.vegetation.models import VegetationObservation
        from apps.satellite.models import SatelliteObservation
        saved = 0

        for record in normalized_data:
            is_sim = record.get("is_simulated", True)
            zone = self._find_nearest_zone(record.get("latitude", 0), record.get("longitude", 0))

            if record.get("index_name"):
                try:
                    acq = record.get("acquisition_date", timezone.now().date())
                    if isinstance(acq, str):
                        from datetime import date as _date
                        acq = _date.fromisoformat(acq[:10])

                    VegetationObservation.objects.create(
                        zone=zone,
                        index_name=record["index_name"],
                        value=record["value"],
                        baseline_value=record.get("baseline_value"),
                        std_dev=record.get("std_dev"),
                        acquisition_date=acq,
                        source=record.get("source", self.name),
                        is_simulated=is_sim,
                        metadata=record.get("metadata", {}),
                    )
                    saved += 1
                except Exception as e:
                    logger.warning("Failed to save vegetation record: %s", str(e))

        return saved

    def _find_nearest_zone(self, lat: float, lng: float):
        """Find the nearest monitoring zone to given coordinates."""
        from apps.geography.models import MonitoringZone
        import math

        zones = list(MonitoringZone.objects.all())
        if not zones:
            return None

        best_zone = None
        best_dist = float("inf")
        for zone in zones:
            dlat = math.radians(zone.latitude - lat)
            dlng = math.radians(zone.longitude - lng)
            a = (math.sin(dlat / 2) ** 2 +
                 math.cos(math.radians(lat)) * math.cos(math.radians(zone.latitude)) *
                 math.sin(dlng / 2) ** 2)
            c = 2 * math.asin(math.sqrt(a))
            dist = 6371 * c
            if dist < best_dist:
                best_dist = dist
                best_zone = zone

        return best_zone

    def generate_demo_data(self, zones=None) -> int:
        """Generate simulated Landsat observations."""
        import random
        from apps.satellite.models import SatelliteObservation
        from apps.vegetation.models import VegetationObservation
        from apps.geography.models import MonitoringZone

        if zones is None:
            zones = list(MonitoringZone.objects.all())
        if not zones:
            return 0

        now = timezone.now()
        count = 0
        for zone in zones:
            for d in range(0, 30, 10):
                for idx_name in ["NDVI", "NDWI"]:
                    val = round(random.uniform(-0.1, 0.8), 4)
                    VegetationObservation.objects.create(
                        zone=zone,
                        index_name=idx_name,
                        value=val,
                        baseline_value=round(val + random.uniform(-0.1, 0.1), 4),
                        std_dev=round(random.uniform(0.05, 0.15), 4),
                        acquisition_date=(now - timedelta(days=d)).date(),
                        source="Landsat (simulé)",
                        is_simulated=True,
                    )
                    count += 1
        return count
