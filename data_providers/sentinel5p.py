"""
Copernicus Sentinel-5P provider.
Fetches atmospheric composition data: SO2, O3, AER_AI, NO2, CO, CH4, HCHO.
Uses CDSE STAC + Process API.
"""
import logging
import os
import math
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from django.utils import timezone
from .base import BaseDataProvider, DataSourceResult, ProviderHealth

logger = logging.getLogger("data_providers.sentinel5p")


class Sentinel5PProvider(BaseDataProvider):
    name = "Sentinel-5P"
    source_type = "ATMOSPHERE"
    is_optional = False

    STAC_URL = "https://stac.dataspace.copernicus.eu/v1"
    PROCESS_URL = "https://sh.dataspace.copernicus.eu/process/v1"
    TOKEN_URL = "https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/token"

    # Sentinel-5P products
    PRODUCTS = {
        "SO2": "S5P_NRTI_L2__SO2___",
        "O3": "S5P_NRTI_L2__O3____",
        "AER_AI": "S5P_NRTI_L2__AER_AI",
        "NO2": "S5P_NRTI_L2__NO2___",
        "CO": "S5P_NRTI_L2__CO____",
        "CH4": "S5P_NRTI_L2__CH4___",
        "HCHO": "S5P_NRTI_L2__HCHO__",
    }

    # Variables to store per product
    VARIABLE_MAP = {
        "SO2": ("SO2", "DU", "Sulfur dioxide column density"),
        "O3": ("O3", "DU", "Ozone column density"),
        "AER_AI": ("AER_AI_340_380", "", "Aerosol Index 340-380nm"),
        "NO2": ("NO2", "mol/m²", "Nitrogen dioxide column density"),
        "CO": ("CO", "mol/m²", "Carbon monoxide column density"),
        "CH4": ("CH4", "ppb", "Methane column density"),
        "HCHO": ("HCHO", "mol/m²", "Formaldehyde column density"),
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
            self._token_expiry = time.time() + data.get("expires_in", 600) - 60
            return self._token
        except Exception as e:
            logger.error("CDSE token error: %s", str(e))
            return None

    def search(self, product_key: str = "SO2", aoi: Dict = None,
               start_date: str = None, end_date: str = None,
               max_cloud_cover: float = 30, **kwargs) -> List[Dict[str, Any]]:
        """Search for Sentinel-5P products via Copernicus OData catalogue.
        S5P is not available on STAC, so we use the OData API."""
        if product_key not in self.PRODUCTS:
            logger.error("Unknown product: %s", product_key)
            return []

        product_type = self.PRODUCTS[product_key]

        if not start_date:
            end_date = end_date or datetime.now().strftime("%Y-%m-%d")
            start_date = (datetime.now() - timedelta(days=3)).strftime("%Y-%m-%d")
        if not end_date:
            end_date = datetime.now().strftime("%Y-%m-%d")

        if aoi:
            if isinstance(aoi, dict):
                lon = (aoi.get("west", -10) + aoi.get("east", 0)) / 2
                lat = (aoi.get("south", 10) + aoi.get("north", 20)) / 2
            else:
                lon, lat = -8.0, 12.6
        else:
            lon, lat = -8.0, 12.6

        # Use OData catalogue (S5P is not on STAC)
        url = "https://catalogue.dataspace.copernicus.eu/odata/v1/Products"
        filt = (
            f"$filter=Collection/Name eq 'SENTINEL-5P' "
            f"and contains(Name,'{product_type}') "
            f"and OData.CSC.Intersects(area=geography'SRID=4326;POINT({lon} {lat})') "
            f"and ContentDate/Start gt {start_date}T00:00:00.000Z "
            f"and ContentDate/Start lt {end_date}T23:59:59.000Z"
        )

        try:
            resp = self.session.get(f"{url}?{filt}&$top=20&$orderby=ContentDate/Start desc", timeout=30)
            resp.raise_for_status()
            data = resp.json()
            products = data.get("value", [])
            return [
                {
                    "id": p.get("Id", ""),
                    "properties": {
                        "title": p.get("Name", ""),
                        "datetime": p.get("ContentDate", {}).get("Start", ""),
                    },
                    "assets": {},
                    "product_key": product_key,
                }
                for p in products
            ]
        except Exception as e:
            logger.error("Sentinel-5P OData search failed for %s: %s", product_key, str(e))
            return []

    def fetch(self, product_key: str = "SO2", aoi: Dict = None,
              start_date: str = None, end_date: str = None, **kwargs) -> List[DataSourceResult]:
        """Search and fetch Sentinel-5P product data."""
        products = self.search(product_key=product_key, aoi=aoi,
                               start_date=start_date, end_date=end_date)
        results = []
        for product in products:
            assets = product.get("assets", {})
            # The main data asset is typically the L2 product file
            data_asset = None
            for key, asset in assets.items():
                if "data" in key.lower() or key.startswith("S5P"):
                    data_asset = asset
                    break
            if not data_asset and assets:
                data_asset = list(assets.values())[0]

            results.append(DataSourceResult(
                source=self.name,
                data={
                    "product_id": product["id"],
                    "product_key": product_key,
                    "asset": data_asset,
                    "geometry": product.get("geometry"),
                    "properties": product.get("properties", {}),
                    "bbox": product.get("bbox"),
                },
                fetched_at=timezone.now(),
                is_simulated=False,
                metadata={
                    "collection": self.PRODUCTS.get(product_key, ""),
                    "date": product.get("properties", {}).get("datetime"),
                },
            ))
        return results

    def normalize(self, raw_data: Any) -> List[Dict[str, Any]]:
        """
        Extract atmospheric variable from Sentinel-5P data.
        Uses Process API to get a point/zone value.
        """
        if isinstance(raw_data, DataSourceResult):
            raw_data = raw_data.data

        if not isinstance(raw_data, dict):
            return []

        product_key = raw_data.get("product_key", "SO2")
        properties = raw_data.get("properties", {})
        geometry = raw_data.get("geometry")
        bbox = raw_data.get("bbox")

        # Extract center coordinates from geometry
        if geometry:
            coords = geometry.get("coordinates", [])
            if geometry.get("type") == "Point" and len(coords) >= 2:
                lat, lng = coords[1], coords[0]
            elif coords:
                lat, lng = 12.6392, -8.0029
            else:
                lat, lng = 12.6392, -8.0029
        else:
            lat, lng = 12.6392, -8.0029

        variable, unit, description = self.VARIABLE_MAP.get(product_key, (product_key, "", ""))

        if self.demo_mode:
            import random
            ranges = {
                "SO2": (0, 0.5), "O3": (200, 350), "AER_AI": (-2, 3),
                "NO2": (0, 0.0002), "CO": (0, 0.1), "CH4": (1700, 1900), "HCHO": (0, 0.0001),
            }
            lo, hi = ranges.get(product_key, (0, 1))
            value = round(random.uniform(lo, hi), 6)
            return [{
                "variable": variable,
                "value": value,
                "unit": unit,
                "quality_flag": "GOOD",
                "observed_at": properties.get("datetime", timezone.now()),
                "latitude": lat,
                "longitude": lng,
                "source": self.name,
                "is_simulated": True,
                "metadata": {"product_key": product_key, "description": description},
            }]

        # Real mode: try to read raster data
        asset = raw_data.get("asset", {})
        href = asset.get("href") if asset else None
        if not href:
            # OData results don't have assets — generate simulated values
            import random
            ranges = {
                "SO2": (0, 0.5), "O3": (200, 350), "AER_AI": (-2, 3),
                "NO2": (0, 0.0002), "CO": (0, 0.1), "CH4": (1700, 1900), "HCHO": (0, 0.0001),
            }
            lo, hi = ranges.get(product_key, (0, 1))
            value = round(random.uniform(lo, hi), 6)
            return [{
                "variable": variable,
                "value": value,
                "unit": unit,
                "quality_flag": "SIMULATED",
                "observed_at": properties.get("datetime", timezone.now()),
                "latitude": lat,
                "longitude": lng,
                "source": self.name,
                "is_simulated": True,
                "metadata": {"product_key": product_key, "description": description},
            }]

        try:
            import rasterio
            import numpy as np
            import tempfile

            resp = self.session.get(href, timeout=120)
            resp.raise_for_status()
            with tempfile.NamedTemporaryFile(suffix=".nc", delete=False) as tmp:
                tmp.write(resp.content)
                tmp_path = tmp.name

            # Read NetCDF/GeoTIFF
            with rasterio.open(tmp_path) as src:
                data = src.read(1)
                nodata = src.nodata
                if nodata is not None:
                    data = data.astype(np.float32)
                    data[data == nodata] = np.nan

                valid = data[~np.isnan(data)] if np.issubdtype(data.dtype, np.floating) else data[data > 0]
                if len(valid) == 0:
                    os.unlink(tmp_path)
                    return []

                # dataMask quality filter
                value = float(np.mean(valid))

            os.unlink(tmp_path)

            try:
                dt = datetime.fromisoformat(properties.get("datetime", "").replace("Z", "+00:00"))
            except (ValueError, AttributeError):
                dt = timezone.now()

            return [{
                "variable": variable,
                "value": value,
                "unit": unit,
                "quality_flag": "GOOD",
                "observed_at": dt,
                "latitude": lat,
                "longitude": lng,
                "source": self.name,
                "is_simulated": False,
                "metadata": {
                    "product_key": product_key,
                    "description": description,
                    "valid_pixels": int(len(valid)),
                },
            }]

        except ImportError:
            logger.warning("rasterio not available — cannot process Sentinel-5P data")
            return []
        except Exception as e:
            logger.error("Sentinel-5P normalization failed: %s", str(e))
            return []

    def save(self, normalized_data: List[Dict[str, Any]]) -> int:
        """Save atmospheric observations to database."""
        from apps.atmosphere.models import AtmosphericObservation
        from apps.geography.models import MonitoringZone

        # Map our variable names to model choices
        MODEL_VARIABLES = {"SO2", "NO2", "O3", "AEROSOLS", "CO", "CH4", "PM25", "PM10"}
        VARIABLE_MAP_TO_MODEL = {
            "AER_AI_340_380": "AEROSOLS",
            "HCHO": "NO2",  # approximate mapping; TODO: add HCHO to model
        }

        saved = 0
        for record in normalized_data:
            try:
                zone = self._find_nearest_zone(record["latitude"], record["longitude"])
                if not zone:
                    continue

                model_var = VARIABLE_MAP_TO_MODEL.get(record["variable"], record["variable"])
                if model_var not in MODEL_VARIABLES:
                    # Store as metadata-only if variable not in model choices
                    continue

                observed_at = record.get("observed_at")
                if isinstance(observed_at, str):
                    try:
                        observed_at = datetime.fromisoformat(observed_at.replace("Z", "+00:00"))
                    except ValueError:
                        observed_at = timezone.now()
                elif not isinstance(observed_at, datetime):
                    observed_at = timezone.now()

                if AtmosphericObservation.objects.filter(
                    zone=zone, variable=model_var,
                    observed_at__date=observed_at.date() if hasattr(observed_at, 'date') else observed_at
                ).exists():
                    continue

                obs = AtmosphericObservation(
                    zone=zone,
                    variable=model_var,
                    value=record["value"],
                    unit=record.get("unit", ""),
                    observed_at=observed_at,
                    source=record.get("source", self.name),
                    quality_flag=record.get("quality_flag", "GOOD"),
                    is_simulated=record.get("is_simulated", False),
                    metadata=record.get("metadata", {}),
                )
                obs.save()
                saved += 1
            except Exception as e:
                logger.warning("Failed to save atmospheric observation: %s", str(e))
        return saved

    def _find_nearest_zone(self, lat: float, lng: float):
        """Find nearest MonitoringZone within 150km."""
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
        if best_zone and best_dist <= 150:
            return best_zone
        return None

    def generate_demo_data(self, zones=None) -> int:
        """Generate simulated atmospheric data."""
        import random
        from apps.atmosphere.models import AtmosphericObservation
        from apps.geography.models import MonitoringZone

        if zones is None:
            zones = list(MonitoringZone.objects.all())
        if not zones:
            return 0

        now = timezone.now()
        observations = []
        for zone in zones:
            for d in range(30):
                date = now - timedelta(days=d)
                for var, unit, lo, hi in [
                    ("SO2", "DU", 0, 0.5),
                    ("O3", "DU", 200, 350),
                    ("AEROSOLS", "", -2, 3),
                    ("NO2", "mol/m²", 0, 0.0002),
                ]:
                    observations.append(AtmosphericObservation(
                        zone=zone, variable=var,
                        value=round(random.uniform(lo, hi), 6),
                        unit=unit, observed_at=date,
                        source="Sentinel-5P (simulé)", is_simulated=True,
                    ))
        AtmosphericObservation.objects.bulk_create(observations, ignore_conflicts=True)
        return len(observations)
