"""
CHIRPS (Climate Hazards Group InfraRed Precipitation with Station data) provider.
Provides precipitation estimates from satellite and ground station data.
Data: GeoTIFF rasters at 5-day, monthly, or daily resolution.
Source: https://data.chc.ucsb.edu/products/CHIRPS-2.0/
"""
import logging
import os
import tempfile
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from django.utils import timezone
from .base import BaseDataProvider, DataSourceResult, ProviderHealth

logger = logging.getLogger("data_providers.chirps")


class CHIRPSProvider(BaseDataProvider):
    name = "CHIRPS"
    source_type = "CLIMATE"
    is_optional = False

    BASE_URL = "https://data.chc.ucsb.edu/products/CHIRPS-2.0"
    # Available: /global/daily/ /global/5day/ /global/monthly/
    # Africa subset: /africa/daily/ /africa/5day/ /africa/monthly/

    def __init__(self, base_url: Optional[str] = None, **kwargs):
        super().__init__(**kwargs)
        self.base_url = base_url or self.BASE_URL
        import requests
        self.session = requests.Session()

    def health_check(self) -> ProviderHealth:
        """CHIRPS is open access, no auth needed."""
        try:
            resp = self.session.head(
                f"{self.base_url}/global/monthly/",
                timeout=15,
            )
            if resp.status_code < 500:
                return ProviderHealth(status="ok")
            return ProviderHealth(status="degraded", reason=f"CHIRPS server returned {resp.status_code}")
        except Exception as e:
            return ProviderHealth(status="error", reason=str(e))

    def search(self, date: str = None, resolution: str = "monthly", **kwargs) -> List[Dict[str, Any]]:
        """
        Search for available CHIRPS data.
        date: YYYY-MM-DD or YYYY-MM
        resolution: 'daily', '5day', 'monthly'
        """
        if not date:
            date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m")

        base = f"{self.base_url}/global/{resolution}"
        if resolution == "monthly":
            filename = f"chirps-v2.0.{date[:7]}.tif.gz"
        elif resolution == "5day":
            filename = f"chirps-v2.0.{date[:7]}.days_p25.tif.gz"
        else:
            filename = f"chirps-v2.0.{date}.tif.gz"

        url = f"{base}/{filename}"
        try:
            resp = self.session.head(url, timeout=15)
            if resp.status_code == 200:
                return [{"url": url, "filename": filename, "date": date, "resolution": resolution}]
        except Exception:
            pass
        return []

    def fetch(self, date: str = None, resolution: str = "monthly",
              bbox: Optional[Dict] = None, **kwargs) -> List[DataSourceResult]:
        """Download CHIRPS GeoTIFF for the given date."""
        if not date:
            date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m")

        results_raw = self.search(date=date, resolution=resolution)
        results = []
        for item in results_raw:
            try:
                resp = self.session.get(item["url"], timeout=60)
                resp.raise_for_status()
                # Save to temp file
                tmp_path = os.path.join(tempfile.gettempdir(), item["filename"])
                with open(tmp_path, "wb") as f:
                    f.write(resp.content)
                results.append(DataSourceResult(
                    source=self.name,
                    data={"path": tmp_path, "url": item["url"], "date": date, "resolution": resolution},
                    fetched_at=timezone.now(),
                    is_simulated=False,
                ))
            except Exception as e:
                logger.error("CHIRPS fetch failed: %s", str(e))
        return results

    def normalize(self, raw_data: Any) -> List[Dict[str, Any]]:
        """
        Extract precipitation values from GeoTIFF raster.
        Uses rasterio/GDAL if available, otherwise returns metadata only.
        """
        if isinstance(raw_data, DataSourceResult):
            raw_data = raw_data.data

        if not isinstance(raw_data, dict):
            return []

        path = raw_data.get("path", "")
        date_str = raw_data.get("date", "")

        try:
            import rasterio
            from rasterio.windows import from_bounds

            records = []
            with rasterio.open(path) as src:
                # If bbox provided, read windowed
                bbox = raw_data.get("bbox")
                if bbox:
                    window = from_bounds(
                        bbox["min_lon"], bbox["min_lat"],
                        bbox["max_lon"], bbox["max_lat"],
                        src.transform
                    )
                    data = src.read(1, window=window)
                else:
                    data = src.read(1)

                # Calculate zonal statistics
                import numpy as np
                valid = data[data != src.nodata] if src.nodata else data[~np.isnan(data)]
                if len(valid) == 0:
                    return []

                # Parse date
                try:
                    if len(date_str) == 7:  # YYYY-MM
                        dt = datetime.strptime(date_str + "-15", "%Y-%m-%d")
                    else:
                        dt = datetime.strptime(date_str, "%Y-%m-%d")
                    observed_at = timezone.make_aware(datetime(dt.year, dt.month, dt.day, 12, 0))
                except ValueError:
                    observed_at = timezone.now()

                records.append({
                    "variable": "PRECIPITATION",
                    "value": float(np.mean(valid)),
                    "unit": "mm",
                    "min_value": float(np.min(valid)),
                    "max_value": float(np.max(valid)),
                    "std_value": float(np.std(valid)),
                    "valid_pixels": int(len(valid)),
                    "observed_at": observed_at,
                    "source": self.name,
                    "is_simulated": False,
                    "metadata": {
                        "resolution": raw_data.get("resolution", ""),
                        "bbox": bbox,
                        "nodata": src.nodata,
                    },
                })
            return records
        except ImportError:
            logger.warning("rasterio not available — cannot process CHIRPS raster")
            return []
        except Exception as e:
            logger.error("CHIRPS normalization failed: %s", str(e))
            return []

    def save(self, normalized_data: List[Dict[str, Any]]) -> int:
        """Save CHIRPS precipitation data to ClimateObservation."""
        from apps.climate.models import ClimateObservation
        from apps.geography.models import MonitoringZone

        saved = 0
        for record in normalized_data:
            try:
                # Find zones from bbox or use all
                zones = list(MonitoringZone.objects.all())
                if record.get("metadata", {}).get("bbox"):
                    # In real implementation, find zones within bbox
                    pass

                for zone in zones[:1]:  # Simplified: assign to first zone
                    if ClimateObservation.objects.filter(
                        zone=zone, variable="PRECIPITATION",
                        observed_at=record["observed_at"], source=self.name
                    ).exists():
                        continue

                    obs = ClimateObservation(
                        zone=zone,
                        variable="PRECIPITATION",
                        value=record["value"],
                        unit=record.get("unit", "mm"),
                        observed_at=record["observed_at"],
                        source=self.name,
                        is_simulated=False,
                        metadata=record.get("metadata", {}),
                    )
                    obs.save()
                    saved += 1
            except Exception as e:
                logger.warning("Failed to save CHIRPS data: %s", str(e))
        return saved

    def generate_demo_data(self, zones=None) -> int:
        """Generate simulated precipitation data for demo."""
        import random
        from apps.climate.models import ClimateObservation
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
                if ClimateObservation.objects.filter(
                    zone=zone, variable="PRECIPITATION", observed_at=date
                ).exists():
                    continue
                observations.append(ClimateObservation(
                    zone=zone, variable="PRECIPITATION",
                    value=round(random.uniform(0, 50), 1),
                    unit="mm", observed_at=date,
                    source="CHIRPS (simulé)", is_simulated=True,
                ))
        ClimateObservation.objects.bulk_create(observations, ignore_conflicts=True)
        return len(observations)
