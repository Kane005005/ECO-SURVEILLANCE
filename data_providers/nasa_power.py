"""
NASA POWER (Prediction of Worldwide Energy Resources) data provider.
Fetches climate/weather data: temperature, humidity, precipitation, wind, radiation, pressure.
API: https://power.larc.nasa.gov/api
"""
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from django.utils import timezone
from .base import BaseDataProvider, DataSourceResult, ProviderHealth

logger = logging.getLogger("data_providers.nasa_power")


class NASAPowerProvider(BaseDataProvider):
    name = "NASA POWER"
    source_type = "CLIMATE"
    is_optional = False

    # POWER API v2 endpoints
    BASE_URL = "https://power.larc.nasa.gov/api/temporal"
    CLIMATE_URL = "https://power.larc.nasa.gov/api/climate"

    # Variables mapping: POWER name → (our model field, unit, description)
    VARIABLE_MAP = {
        "T2M": ("TEMPERATURE", "°C", "Temperature at 2m"),
        "T2M_MAX": ("TEMPERATURE_MAX", "°C", "Max temperature at 2m"),
        "T2M_MIN": ("TEMPERATURE_MIN", "°C", "Min temperature at 2m"),
        "RH2M": ("HUMIDITY", "%", "Relative humidity at 2m"),
        "PRECTOTCORR": ("PRECIPITATION", "mm/day", "Precipitation corrected"),
        "WS2M": ("WIND_SPEED", "m/s", "Wind speed at 2m"),
        "WD2M": ("WIND_DIRECTION", "°", "Wind direction at 2m"),
        "PS": ("PRESSURE", "kPa", "Surface pressure"),
        "ALLSKY_KT": ("RADIATION", "dimensionless", "Clearness index"),
        "ALLSKY_SFC_SW_DWN": ("SOLAR_RADIATION", "W/m²", "Solar radiation"),
    }

    # Climate variables to fetch
    DEFAULT_VARIABLES = ["T2M", "T2M_MAX", "T2M_MIN", "RH2M", "PRECTOTCORR", "WS2M", "PS"]

    def __init__(self, base_url: Optional[str] = None, **kwargs):
        super().__init__(**kwargs)
        self.base_url = base_url or self.BASE_URL
        import requests
        self.session = requests.Session()

    def health_check(self) -> ProviderHealth:
        """NASA POWER is open access — no API key needed."""
        try:
            resp = self.session.get(
                f"{self.base_url}/daily/point",
                params={"parameters": "T2M", "community": "AG", "longitude": -8.0, "latitude": 12.6, "start": "20240101", "end": "20240102", "format": "JSON"},
                timeout=15,
            )
            if resp.status_code == 200:
                return ProviderHealth(status="ok")
            return ProviderHealth(status="degraded", reason=f"POWER API returned {resp.status_code}")
        except Exception as e:
            return ProviderHealth(status="error", reason=str(e))

    def search(self, latitude: float = 12.6392, longitude: float = -8.0029,
               start_date: str = None, end_date: str = None, **kwargs) -> List[Dict[str, Any]]:
        """Search for available climate data at a point."""
        if not start_date:
            end_date = end_date or datetime.now().strftime("%Y%m%d")
            start_date = (datetime.now() - timedelta(days=30)).strftime("%Y%m%d")
        if not end_date:
            end_date = datetime.now().strftime("%Y%m%d")

        params = {
            "parameters": ",".join(self.DEFAULT_VARIABLES),
            "community": "AG",
            "longitude": longitude,
            "latitude": latitude,
            "start": start_date,
            "end": end_date,
            "format": "JSON",
        }
        try:
            resp = self.session.get(f"{self.base_url}/daily/point", params=params, timeout=30)
            resp.raise_for_status()
            data = resp.json()
            return [{"type": "point", "data": data, "lat": latitude, "lon": longitude}]
        except Exception as e:
            logger.error("POWER search failed: %s", str(e))
            return []

    def fetch(self, latitude: float = 12.6392, longitude: float = -8.0029,
              start_date: str = None, end_date: str = None, **kwargs) -> List[DataSourceResult]:
        """Fetch climate data from NASA POWER."""
        results_raw = self.search(latitude=latitude, longitude=longitude,
                                  start_date=start_date, end_date=end_date)
        results = []
        for item in results_raw:
            results.append(DataSourceResult(
                source=self.name,
                data=item,
                fetched_at=timezone.now(),
                is_simulated=False,
                metadata={"lat": latitude, "lon": longitude},
            ))
        return results

    def normalize(self, raw_data: Any) -> List[Dict[str, Any]]:
        """Normalize POWER API response into per-day climate observations."""
        if isinstance(raw_data, DataSourceResult):
            raw_data = raw_data.data

        if not isinstance(raw_data, dict) or "data" not in raw_data:
            return []

        api_data = raw_data["data"]
        properties = api_data.get("properties", {})
        parameter_data = properties.get("parameter", {})
        lat = raw_data.get("lat", 0)
        lon = raw_data.get("lon", 0)

        records = []
        # Collect all dates from any variable
        all_dates = set()
        for param_name, values in parameter_data.items():
            if isinstance(values, dict):
                all_dates.update(values.keys())

        for date_str in sorted(all_dates):
            if date_str == "珊瑚" or len(date_str) != 8:  # skip metadata keys
                continue
            for param_name, values in parameter_data.items():
                if not isinstance(values, dict) or param_name not in self.VARIABLE_MAP:
                    continue
                value = values.get(date_str)
                if value is None or value == -999.0:  # POWER uses -999 as missing
                    continue
                model_field, unit, description = self.VARIABLE_MAP[param_name]
                try:
                    dt = datetime.strptime(date_str, "%Y%m%d")
                    observed_at = timezone.make_aware(datetime(dt.year, dt.month, dt.day, 12, 0))
                except ValueError:
                    continue
                records.append({
                    "variable": model_field,
                    "value": float(value),
                    "unit": unit,
                    "observed_at": observed_at,
                    "latitude": lat,
                    "longitude": lon,
                    "source": self.name,
                    "is_simulated": False,
                    "metadata": {"power_variable": param_name, "description": description},
                })
        return records

    def save(self, normalized_data: List[Dict[str, Any]]) -> int:
        """Save climate observations to database."""
        from apps.climate.models import ClimateObservation
        from apps.geography.models import MonitoringZone

        saved = 0
        for record in normalized_data:
            try:
                zone = self._find_nearest_zone(record["latitude"], record["longitude"])
                if not zone:
                    continue

                # Dedup: same zone + variable + observed_at
                if ClimateObservation.objects.filter(
                    zone=zone, variable=record["variable"],
                    observed_at=record["observed_at"]
                ).exists():
                    continue

                obs = ClimateObservation(
                    zone=zone,
                    variable=record["variable"],
                    value=record["value"],
                    unit=record.get("unit", ""),
                    observed_at=record["observed_at"],
                    source=record.get("source", self.name),
                    is_simulated=False,
                    metadata=record.get("metadata", {}),
                )
                obs.save()
                saved += 1
            except Exception as e:
                logger.warning("Failed to save climate observation: %s", str(e))
        return saved

    def _find_nearest_zone(self, lat: float, lng: float):
        """Find nearest MonitoringZone within 150km."""
        from apps.geography.models import MonitoringZone
        import math

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
        """Generate simulated climate data for demo mode."""
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
                for var, unit, lo, hi in [
                    ("TEMPERATURE", "°C", 25, 45),
                    ("PRECIPITATION", "mm", 0, 50),
                    ("HUMIDITY", "%", 20, 90),
                    ("WIND_SPEED", "m/s", 0, 15),
                    ("PRESSURE", "kPa", 95, 105),
                    ("RADIATION", "W/m²", 100, 700),
                ]:
                    observations.append(ClimateObservation(
                        zone=zone, variable=var,
                        value=round(random.uniform(lo, hi), 1),
                        unit=unit, observed_at=date,
                        source="NASA POWER (simulé)", is_simulated=True,
                    ))
        ClimateObservation.objects.bulk_create(observations, ignore_conflicts=True)
        return len(observations)
