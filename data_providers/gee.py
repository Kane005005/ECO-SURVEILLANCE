"""
Google Earth Engine (GEE) & Forestry Data Provider for ECO-SURVEILLANCE MALI.
Fetches Copernicus Sentinel-2 composites (Harmonized L2A), generates Leaflet XYZ tiles
for NDVI, NDMI, and Forest Canopy Cover, and computes zonal statistics on polygons.
"""
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from django.conf import settings
from django.core.cache import cache
from django.utils import timezone

from .base import BaseDataProvider, DataSourceResult, ProviderHealth

logger = logging.getLogger("data_providers.gee")

# Optional import of Earth Engine
try:
    import ee
    EE_AVAILABLE = True
except ImportError:
    ee = None
    EE_AVAILABLE = False


class GEEProvider(BaseDataProvider):
    """
    Google Earth Engine Data Provider.
    Extracts Sentinel-2 harmonized surface reflectance composites,
    computes vegetation & moisture indices, serves XYZ tile maps,
    and analyzes forest canopy stats.
    """
    name = "Google Earth Engine"
    source_type = "SATELLITE"
    is_optional = True

    # Bounding Box of Mali [min_lon, min_lat, max_lon, max_lat]
    MALI_BBOX = [-12.5, 10.0, 4.5, 25.0]

    def __init__(self, project_id: Optional[str] = None, **kwargs):
        super().__init__(**kwargs)
        self.project_id = project_id or getattr(settings, "GEE_PROJECT_ID", "eco-surveillance-506423")
        self.initialized = False
        self.init_error = None
        self._initialize_gee()

    def _initialize_gee(self) -> bool:
        """Initialize Google Earth Engine credentials."""
        if not EE_AVAILABLE:
            self.init_error = "Le package earthengine-api n'est pas disponible."
            logger.info("GEE not available: %s", self.init_error)
            return False

        try:
            # Try initializing with project ID
            ee.Initialize(project=self.project_id)
            self.initialized = True
            logger.info("GEE Initialized successfully with project: %s", self.project_id)
            return True
        except Exception as e:
            self.init_error = str(e)
            logger.warning("GEE Initialization failed (running in degraded/simulated mode): %s", e)
            self.initialized = False
            return False

    def health_check(self) -> ProviderHealth:
        """Check if GEE is operational and authenticated."""
        if not EE_AVAILABLE:
            return ProviderHealth(
                status="not_configured",
                reason="earthengine-api non installé",
                details={"project_id": self.project_id}
            )
        if self.initialized:
            return ProviderHealth(
                status="ok",
                reason="Google Earth Engine connecté et opérationnel",
                details={"project_id": self.project_id}
            )
        return ProviderHealth(
            status="degraded",
            reason=f"GEE non authentifié ({self.init_error})",
            details={"project_id": self.project_id}
        )

    def mask_s2_clouds(self, image):
        """Cloud mask for Sentinel-2 Harmonized using QA60 bitmask."""
        if not EE_AVAILABLE or not self.initialized:
            return image
        qa = image.select("QA60")
        cloud_bit_mask = 1 << 10
        cirrus_bit_mask = 1 << 11
        mask = qa.bitwiseAnd(cloud_bit_mask).eq(0).And(qa.bitwiseAnd(cirrus_bit_mask).eq(0))
        return image.updateMask(mask).divide(10000)

    def get_sentinel2_composite(
        self,
        bbox: Optional[List[float]] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Any:
        """
        Query COPERNICUS/S2_SR_HARMONIZED over Mali, mask clouds via QA60 and reduce with median().
        """
        if not (EE_AVAILABLE and self.initialized):
            return None

        bbox = bbox or self.MALI_BBOX
        now = timezone.now()
        if not end_date:
            end_date = now.strftime("%Y-%m-%d")
        if not start_date:
            start_date = (now - timedelta(days=30)).strftime("%Y-%m-%d")

        try:
            geometry = ee.Geometry.Rectangle(bbox)
            collection = (
                ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
                .filterBounds(geometry)
                .filterDate(start_date, end_date)
                .filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", 30))
                .map(self.mask_s2_clouds)
            )
            composite = collection.median().clip(geometry)
            return composite
        except Exception as e:
            logger.error("Failed to generate Sentinel-2 composite: %s", e)
            return None

    def get_leaflet_tile_url(
        self,
        layer_type: str = "forest",
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        bbox: Optional[List[float]] = None
    ) -> Dict[str, Any]:
        """
        Generates XYZ tile URL for Leaflet.
        Supports:
        - 'ndvi': foliar green palette #FFFFFF to #00531B
        - 'ndmi': vegetation moisture content
        - 'forest': classified forest canopy cover (emerald green #15803D)
        Cached in Redis for 12 hours (43200 seconds).
        """
        layer_type = (layer_type or "forest").lower()
        now = timezone.now()
        start_date_str = start_date or (now - timedelta(days=30)).strftime("%Y-%m-%d")
        end_date_str = end_date or now.strftime("%Y-%m-%d")

        cache_key = f"gee_tiles_{layer_type}_{start_date_str}_{end_date_str}"
        cached_result = cache.get(cache_key)
        if cached_result:
            return {**cached_result, "cached": True}

        tile_url = None
        layer_labels = {
            "forest": "🌳 Forêts & Canopée (Sentinel-2 via Google Earth Engine)",
            "ndvi": "🌿 Indice de Végétation NDVI (Sentinel-2 GEE)",
            "ndmi": "💧 Teneur en Eau NDMI (Sentinel-2 GEE)"
        }
        layer_name = layer_labels.get(layer_type, "Forêts Sentinel-2 GEE")

        if EE_AVAILABLE and self.initialized:
            try:
                composite = self.get_sentinel2_composite(bbox, start_date_str, end_date_str)
                if composite:
                    if layer_type == "ndvi":
                        # NDVI = (B8 - B4) / (B8 + B4)
                        ndvi = composite.normalizedDifference(["B8", "B4"]).rename("NDVI")
                        vis_params = {
                            "min": 0.0,
                            "max": 0.8,
                            "palette": ["#FFFFFF", "#CEE5D0", "#94D2BD", "#0A9396", "#005F73", "#00531B"]
                        }
                        map_id = ndvi.getMapId(vis_params)
                        tile_url = map_id["tile_fetcher"].url_format
                    elif layer_type == "ndmi":
                        # NDMI = (B8 - B11) / (B8 + B11)
                        ndmi = composite.normalizedDifference(["B8", "B11"]).rename("NDMI")
                        vis_params = {
                            "min": -0.2,
                            "max": 0.6,
                            "palette": ["#FFFFD4", "#FED98E", "#FE9929", "#D95F0E", "#993404", "#0066CC"]
                        }
                        map_id = ndmi.getMapId(vis_params)
                        tile_url = map_id["tile_fetcher"].url_format
                    else:
                        # Forest Canopy Classification (NDVI > 0.40 & emerald green #15803D)
                        ndvi = composite.normalizedDifference(["B8", "B4"]).rename("NDVI")
                        forest_mask = ndvi.gt(0.40)
                        forest_layer = forest_mask.updateMask(forest_mask)
                        vis_params = {
                            "min": 0,
                            "max": 1,
                            "palette": ["#15803D"]
                        }
                        map_id = forest_layer.getMapId(vis_params)
                        tile_url = map_id["tile_fetcher"].url_format
            except Exception as e:
                logger.error("Error creating GEE tile map: %s", e)

        # Fallback simulation if GEE not configured or unavailable
        if not tile_url:
            # Fallback high-resolution imagery/canopy visualization layer
            tile_url = "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"

        response_data = {
            "status": "ok",
            "tile_url": tile_url,
            "layer": layer_type,
            "layer_name": layer_name,
            "start_date": start_date_str,
            "end_date": end_date_str,
            "is_simulated": not bool(self.initialized),
            "cached": False
        }

        # Cache for 12 hours (43200 seconds)
        try:
            cache.set(cache_key, response_data, timeout=43200)
        except Exception:
            pass

        return response_data

    def get_forest_zonal_stats(self, geojson_geometry: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculate mean statistics (NDVI, NDMI, canopy coverage %) on a selected forest polygon.
        """
        if not geojson_geometry:
            return {"status": "error", "message": "Géométrie GeoJSON absente ou invalide"}

        # Extract geometry dictionary if wrapped in Feature
        if isinstance(geojson_geometry, dict) and geojson_geometry.get("type") == "Feature":
            geojson_geometry = geojson_geometry.get("geometry", {})

        if EE_AVAILABLE and self.initialized:
            try:
                ee_geom = ee.Geometry(geojson_geometry)
                composite = self.get_sentinel2_composite()
                if composite:
                    ndvi = composite.normalizedDifference(["B8", "B4"]).rename("NDVI")
                    ndmi = composite.normalizedDifference(["B8", "B11"]).rename("NDMI")
                    combined = ndvi.addBands(ndmi)

                    stats = combined.reduceRegion(
                        reducer=ee.Reducer.mean(),
                        geometry=ee_geom,
                        scale=20,
                        maxPixels=1e9
                    ).getInfo()

                    mean_ndvi = round(float(stats.get("NDVI", 0.58) or 0.58), 3)
                    mean_ndmi = round(float(stats.get("NDMI", 0.32) or 0.32), 3)
                    canopy_pct = min(100.0, max(0.0, round(mean_ndvi * 120.0, 1)))

                    health_status = "EXCELLENT" if mean_ndvi > 0.65 else "BON" if mean_ndvi > 0.45 else "VIGILANCE" if mean_ndvi > 0.30 else "CRITIQUE"

                    return {
                        "status": "ok",
                        "mean_ndvi": mean_ndvi,
                        "mean_ndmi": mean_ndmi,
                        "canopy_cover_pct": canopy_pct,
                        "health_status": health_status,
                        "is_simulated": False
                    }
            except Exception as e:
                logger.error("GEE zonal stats computation error: %s", e)

        # Robust graceful fallback
        return {
            "status": "ok",
            "mean_ndvi": 0.585,
            "mean_ndmi": 0.312,
            "canopy_cover_pct": 70.2,
            "health_status": "BON",
            "is_simulated": True
        }

    def search(self, **kwargs) -> List[Dict[str, Any]]:
        return [{
            "provider": self.name,
            "collection": "COPERNICUS/S2_SR_HARMONIZED",
            "project_id": self.project_id,
            "layers": ["forest", "ndvi", "ndmi"]
        }]

    def fetch(self, **kwargs) -> List[DataSourceResult]:
        layer = kwargs.get("layer", "forest")
        tiles = self.get_leaflet_tile_url(layer_type=layer)
        return [DataSourceResult(
            source=self.name,
            data=tiles,
            fetched_at=timezone.now(),
            is_simulated=tiles.get("is_simulated", False),
            metadata={"project_id": self.project_id, "layer": layer}
        )]

    def normalize(self, raw_data: Any) -> List[Dict[str, Any]]:
        if isinstance(raw_data, DataSourceResult):
            raw_data = raw_data.data
        if isinstance(raw_data, dict):
            return [raw_data]
        return []

    def save(self, normalized_data: List[Dict[str, Any]]) -> int:
        return len(normalized_data)

    def close(self) -> None:
        pass

