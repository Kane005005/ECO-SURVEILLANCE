"""
OpenAQ v3 provider.
Fetches air quality measurements from the OpenAQ network.
API: https://api.openaq.org/v3/
"""
import logging
import os
import math
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from django.utils import timezone
from .base import BaseDataProvider, DataSourceResult, ProviderHealth

logger = logging.getLogger("data_providers.openaq")


class OpenAQProvider(BaseDataProvider):
    name = "OpenAQ"
    source_type = "AIR_QUALITY"
    is_optional = True

    BASE_URL = "https://api.openaq.org/v3"

    # Parameters we care about
    PARAMETER_MAP = {
        "pm25": ("PM25", "µg/m³", "Fine particulate matter"),
        "pm10": ("PM10", "µg/m³", "Coarse particulate matter"),
        "no2": ("NO2", "µg/m³", "Nitrogen dioxide"),
        "o3": ("O3", "µg/m³", "Ozone"),
        "so2": ("SO2", "µg/m³", "Sulfur dioxide"),
        "co": ("CO", "µg/m³", "Carbon monoxide"),
    }

    def __init__(self, api_key: str = "", **kwargs):
        super().__init__(**kwargs)
        self.api_key = api_key or os.environ.get("OPENAQ_API_KEY", "")
        import requests
        self.session = requests.Session()
        if self.api_key:
            self.session.headers.update({"X-API-Key": self.api_key})

    def health_check(self) -> ProviderHealth:
        if not self.api_key:
            return ProviderHealth(
                status="not_configured",
                reason="OPENAQ_API_KEY missing",
            )
        try:
            resp = self.session.get(f"{self.BASE_URL}/locations?limit=1", timeout=10)
            resp.raise_for_status()
            return ProviderHealth(
                status="ok",
                details={"locations_found": resp.json().get("meta", {}).get("found", 0)},
            )
        except Exception as e:
            return ProviderHealth(
                status="error",
                reason=str(e),
            )

    def search(self, latitude: float = None, longitude: float = None,
               radius_km: float = 25, parameters: List[str] = None,
               country_code: str = "ML", limit: int = 50, **kwargs) -> List[Dict]:
        """Search for OpenAQ monitoring locations.
        v3 API: uses bbox or coordinates with max 25km radius."""
        if not self.api_key:
            return []

        params = {"limit": min(limit, 100)}
        if latitude and longitude:
            # Use bbox (lon ± radius, lat ± radius)
            import math
            radius_deg = radius_km / 111.0  # approx degrees
            params["bbox"] = f"{longitude - radius_deg},{latitude - radius_deg},{longitude + radius_deg},{latitude + radius_deg}"
        if country_code:
            params["country"] = country_code

        try:
            resp = self.session.get(f"{self.BASE_URL}/locations", params=params, timeout=30)
            resp.raise_for_status()
            data = resp.json()
            return data.get("results", [])
        except Exception as e:
            logger.error("OpenAQ search failed: %s", str(e))
            return []

    def fetch(self, location_id: int = None, parameter: str = None,
              date_from: str = None, date_to: str = None,
              limit: int = 1000, **kwargs) -> List[DataSourceResult]:
        """Fetch measurements from a specific location."""
        if not self.api_key:
            return []

        results_list = []

        if location_id:
            locations = [{"id": location_id}]
        else:
            locations = self.search(limit=10)

        for loc in locations[:5]:  # Limit to avoid rate limiting
            loc_id = loc.get("id") if isinstance(loc, dict) else loc
            params = {"location_id": loc_id, "limit": limit, "order": "desc"}
            if parameter:
                params["parameter"] = parameter
            if date_from:
                params["date_from"] = date_from
            if date_to:
                params["date_to"] = date_to

            try:
                resp = self.session.get(f"{self.BASE_URL}/measurements", params=params, timeout=30)
                resp.raise_for_status()
                data = resp.json()
                measurements = data.get("results", [])

                if measurements:
                    # Get location info
                    loc_info = None
                    try:
                        loc_resp = self.session.get(f"{self.BASE_URL}/locations/{loc_id}", timeout=10)
                        if loc_resp.ok:
                            loc_info = loc_resp.json().get("results", [{}])[0]
                    except Exception:
                        pass

                    results_list.append(DataSourceResult(
                        source=self.name,
                        data={
                            "location_id": loc_id,
                            "location_name": loc_info.get("name", "") if loc_info else "",
                            "coordinates": loc_info.get("coordinates", {}) if loc_info else {},
                            "country": loc_info.get("country", {}).get("code", "") if loc_info else "",
                            "measurements": measurements,
                        },
                        fetched_at=timezone.now(),
                        is_simulated=False,
                        metadata={
                            "count": len(measurements),
                            "parameter": parameter,
                        },
                    ))

            except Exception as e:
                logger.warning("OpenAQ fetch failed for location %s: %s", loc_id, e)
                continue

        return results_list

    def normalize(self, raw_data: Any, **kwargs) -> List[Dict[str, Any]]:
        """Normalize OpenAQ measurements to standard format."""
        if isinstance(raw_data, DataSourceResult):
            raw_data = raw_data.data

        if not isinstance(raw_data, dict):
            return []

        location_id = raw_data.get("location_id", 0)
        location_name = raw_data.get("location_name", "")
        coordinates = raw_data.get("coordinates", {})
        measurements = raw_data.get("measurements", [])

        lat = coordinates.get("latitude", 0)
        lng = coordinates.get("longitude", 0)

        normalized = []
        for m in measurements:
            param_name = m.get("parameter", {}).get("name", "")
            value = m.get("value", 0)
            unit = m.get("parameter", {}).get("units", "")
            date_info = m.get("date", {})
            datetime_str = date_info.get("utc", date_info.get("local", ""))

            # Map to our variable names
            mapped = self.PARAMETER_MAP.get(param_name.lower(), (param_name, unit, ""))

            try:
                dt = datetime.fromisoformat(datetime_str.replace("Z", "+00:00")) if datetime_str else timezone.now()
            except (ValueError, AttributeError):
                dt = timezone.now()

            normalized.append({
                "latitude": lat,
                "longitude": lng,
                "location_id": location_id,
                "location_name": location_name,
                "variable": mapped[0],
                "value": float(value),
                "unit": mapped[1] or unit,
                "measured_at": dt,
                "source": self.name,
                "parameter_original": param_name,
            })

        return normalized

    def save(self, observations: List[Dict], **kwargs) -> int:
        """Save air quality observations to database."""
        if not observations:
            return 0

        from apps.atmosphere.models import AtmosphericObservation
        from apps.geography.models import MonitoringZone

        saved = 0
        for obs in observations:
            try:
                lat = obs.get("latitude", 0)
                lng = obs.get("longitude", 0)
                zone = self._find_nearest_zone(lat, lng)
                if not zone:
                    continue

                variable = obs.get("variable", "")
                measured_at = obs.get("measured_at", timezone.now())
                if hasattr(measured_at, "timezone_aware") and not measured_at.tzinfo:
                    measured_at = timezone.make_aware(measured_at) if timezone.is_naive(measured_at) else measured_at

                # Dedup
                exists = AtmosphericObservation.objects.filter(
                    zone=zone, variable=variable,
                    observed_at__date=measured_at.date() if hasattr(measured_at, "date") else measured_at,
                ).exists()
                if exists:
                    continue

                AtmosphericObservation.objects.create(
                    zone=zone,
                    variable=variable,
                    value=obs.get("value", 0),
                    unit=obs.get("unit", ""),
                    observed_at=measured_at,
                    source=self.name,
                    quality_flag="VERIFIED",
                    is_simulated=False,
                    metadata={
                        "openaq_location_id": obs.get("location_id"),
                        "openaq_location_name": obs.get("location_name"),
                        "parameter_original": obs.get("parameter_original"),
                    },
                )
                saved += 1
            except Exception as e:
                logger.warning("Failed to save OpenAQ observation: %s", e)
                continue

        return saved

    def _find_nearest_zone(self, lat: float, lng: float, max_distance_km: float = 150):
        """Find nearest monitoring zone using Haversine."""
        from apps.geography.models import MonitoringZone

        zones = MonitoringZone.objects.exclude(latitude__isnull=True).exclude(longitude__isnull=True)
        nearest = None
        min_dist = max_distance_km

        for zone in zones:
            dlat = math.radians(zone.latitude - lat)
            dlng = math.radians(zone.longitude - lng)
            a = (math.sin(dlat / 2) ** 2 +
                 math.cos(math.radians(lat)) * math.cos(math.radians(zone.latitude)) *
                 math.sin(dlng / 2) ** 2)
            c = 2 * math.asin(math.sqrt(a))
            dist = 6371 * c
            if dist < min_dist:
                min_dist = dist
                nearest = zone

        return nearest

    def generate_demo_data(self):
        """Generate demo air quality data."""
        from apps.geography.models import MonitoringZone
        from apps.atmosphere.models import AtmosphericObservation
        import random

        zones = MonitoringZone.objects.all()
        now = timezone.now()
        count = 0

        demo_params = [
            ("PM25", "µg/m³", 10, 80),
            ("PM10", "µg/m³", 20, 150),
            ("NO2", "µg/m³", 5, 60),
            ("O3", "µg/m³", 30, 120),
            ("SO2", "µg/m³", 2, 40),
            ("CO", "µg/m³", 200, 2000),
        ]

        for zone in zones:
            for i in range(30):
                var, unit, vmin, vmax = random.choice(demo_params)
                dt = now - timedelta(days=i, hours=random.randint(0, 23))

                exists = AtmosphericObservation.objects.filter(
                    zone=zone, variable=var,
                    observed_at__date=dt.date(),
                ).exists()
                if exists:
                    continue

                AtmosphericObservation.objects.create(
                    zone=zone,
                    variable=var,
                    value=random.uniform(vmin, vmax),
                    unit=unit,
                    observed_at=dt,
                    source="OpenAQ (demo)",
                    quality_flag="SIMULATED",
                    is_simulated=True,
                    metadata={"demo": True},
                )
                count += 1

        return count
