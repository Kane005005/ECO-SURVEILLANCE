"""
NASA FIRMS data provider.
Fetches active fire detections from NASA FIRMS REST API.
Supports MODIS and VIIRS satellites.
"""
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from django.utils import timezone
from .base import BaseDataProvider, DataSourceResult, ProviderHealth

logger = logging.getLogger("data_providers.firms")


class FIRMSProvider(BaseDataProvider):
    name = "NASA FIRMS"
    source_type = "FIRE"
    is_optional = False

    BASE_URL = "https://firms.modaps.eosdis.nasa.gov/api/area"

    def __init__(self, map_key: Optional[str] = None, source: str = "VIIRS", **kwargs):
        super().__init__(**kwargs)
        self.map_key = map_key
        self.source = source
        import requests
        self.session = requests.Session()

    def health_check(self) -> ProviderHealth:
        if not self.map_key:
            return ProviderHealth(status="not_configured", reason="FIRMS_MAP_KEY manquant")
        return ProviderHealth(status="ok")

    def search(self, country: str = "MLI", days: int = 1, bbox: Optional[Dict] = None, **kwargs) -> List[Dict[str, Any]]:
        """Search for active fires. Returns list of fire detections.
        Uses FIRMS v2 area API: area/csv/{key}/{source}/{west,south,east,north}/{days}"""
        # Default bbox covers all of Mali + buffer
        if not bbox:
            bbox = {"min_lon": -12, "min_lat": 10, "max_lon": 4, "max_lat": 25}

        endpoint = f"{self.BASE_URL}/csv/{self.map_key}/{self.source}/{bbox['min_lon']},{bbox['min_lat']},{bbox['max_lon']},{bbox['max_lat']}/{days}"
        try:
            response = self.session.get(endpoint, timeout=30)
            response.raise_for_status()
            # CSV response: parse header + rows
            lines = response.text.strip().split("\n")
            if len(lines) < 2:
                return []
            header = lines[0].split(",")
            records = []
            for line in lines[1:]:
                values = line.split(",")
                if len(values) >= len(header):
                    record = dict(zip(header, values))
                    records.append(record)
            return records
        except Exception as e:
            logger.error("FIRMS search failed: %s", str(e))
            return []

    def fetch(self, country: str = "MLI", days: int = 1, bbox: Optional[Dict] = None, **kwargs) -> List[DataSourceResult]:
        """Fetch active fires and return as DataSourceResult list."""
        fires = self.search(country=country, days=days, bbox=bbox)
        results = []
        for fire in fires:
            results.append(DataSourceResult(
                source=self.name,
                data=fire,
                fetched_at=timezone.now(),
                is_simulated=False,
                metadata={"satellite": self.source, "country": country},
            ))
        return results

    def normalize(self, raw_data: Any) -> List[Dict[str, Any]]:
        """Normalize FIRMS JSON response into standard fire detection format."""
        if isinstance(raw_data, DataSourceResult):
            raw_data = raw_data.data

        if not isinstance(raw_data, dict):
            return []

        # FIRMS API returns fields like latitude, longitude, bright_ti4, scan, track, acq_date, etc.
        record = {
            "latitude": float(raw_data.get("latitude", 0)),
            "longitude": float(raw_data.get("longitude", 0)),
            "detected_at": self._parse_firms_datetime(raw_data),
            "satellite": raw_data.get("satellite", self.source),
            "confidence": raw_data.get("confidence", "nominal"),
            "brightness": self._safe_float(raw_data.get("bright_ti4") or raw_data.get("bright_ti5")),
            "frp": self._safe_float(raw_data.get("frp")),
            "scan": self._safe_float(raw_data.get("scan")),
            "track": self._safe_float(raw_data.get("track")),
            "bright_t31": self._safe_float(raw_data.get("bright_t31")),
            "daynight": raw_data.get("daynight", "D"),
            "source": self.name,
            "is_simulated": False,
            "metadata": {
                "instrument": raw_data.get("instrument", ""),
                "version": raw_data.get("version", ""),
                "bright_ti4": raw_data.get("bright_ti4"),
                "bright_ti5": raw_data.get("bright_ti5"),
            },
        }
        return [record]

    def save(self, normalized_data: List[Dict[str, Any]]) -> int:
        """Save fire detections to database. Associates with nearest MonitoringZone."""
        from apps.fires.models import FireDetection
        from apps.geography.models import MonitoringZone

        saved = 0
        for record in normalized_data:
            try:
                # Skip if already exists (approximate dedup by coords + time)
                lat, lng = record["latitude"], record["longitude"]
                det_at = record["detected_at"]
                if FireDetection.objects.filter(
                    latitude=lat, longitude=lng,
                    detected_at=det_at
                ).exists():
                    continue

                # Find nearest zone
                zone = self._find_nearest_zone(lat, lng)

                fire = FireDetection(
                    latitude=lat,
                    longitude=lng,
                    detected_at=det_at,
                    satellite=record.get("satellite", ""),
                    confidence=record.get("confidence", "nominal"),
                    brightness=record.get("brightness"),
                    frp=record.get("frp"),
                    scan=record.get("scan"),
                    track=record.get("track"),
                    bright_t31=record.get("bright_t31"),
                    daynight=record.get("daynight", "D"),
                    source=record.get("source", self.name),
                    is_simulated=False,
                    zone=zone,
                    metadata=record.get("metadata", {}),
                )
                fire.save()
                saved += 1
            except Exception as e:
                logger.warning("Failed to save fire detection: %s", str(e))
        return saved

    def _find_nearest_zone(self, lat: float, lng: float):
        """Find the nearest MonitoringZone within reasonable distance."""
        from apps.geography.models import MonitoringZone
        import math

        zones = MonitoringZone.objects.exclude(latitude__isnull=True).exclude(longitude__isnull=True)
        best_zone = None
        best_dist = float("inf")
        for zone in zones:
            dlat = math.radians(zone.latitude - lat)
            dlng = math.radians(zone.longitude - lng)
            a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat)) * math.cos(math.radians(zone.latitude)) * math.sin(dlng / 2) ** 2
            dist = 2 * 6371 * math.asin(math.sqrt(a))  # km
            if dist < best_dist:
                best_dist = dist
                best_zone = zone
        # Only associate if within 100km
        if best_zone and best_dist <= 100:
            return best_zone
        return None

    def _parse_firms_datetime(self, data: Dict) -> datetime:
        """Parse FIRMS acquisition datetime from various field formats."""
        # FIRMS uses acq_date + acq_time or similar
        acq_date = data.get("acq_date", "")
        acq_time = data.get("acq_time", "0000")
        if acq_date:
            try:
                time_str = str(acq_time).zfill(4)
                hour = int(time_str[:2])
                minute = int(time_str[2:])
                from datetime import date as dt_date
                d = datetime.strptime(acq_date, "%Y-%m-%d").date()
                return timezone.make_aware(datetime(d.year, d.month, d.day, hour, minute))
            except (ValueError, TypeError):
                pass
        return timezone.now()

    @staticmethod
    def _safe_float(val) -> Optional[float]:
        try:
            return float(val) if val is not None else None
        except (ValueError, TypeError):
            return None

    def generate_demo_data(self, zones=None) -> int:
        """Generate simulated fire data for demo mode."""
        import random
        from apps.fires.models import FireDetection
        from apps.geography.models import MonitoringZone

        if zones is None:
            zones = list(MonitoringZone.objects.all())
        if not zones:
            return 0

        now = timezone.now()
        fires = []
        for _ in range(60):
            zone = random.choice(zones)
            days_ago = random.randint(0, 14)
            fires.append(FireDetection(
                latitude=zone.latitude + random.uniform(-2, 2),
                longitude=zone.longitude + random.uniform(-2, 2),
                detected_at=now - timedelta(days=days_ago, hours=random.randint(0, 23)),
                satellite=random.choice(["MODIS", "VIIRS"]),
                confidence=random.choice(["low", "nominal", "high"]),
                brightness=round(random.uniform(300, 500), 1),
                frp=round(random.uniform(5, 200), 1),
                source="NASA FIRMS (simulé)",
                is_simulated=True,
                zone=zone,
            ))
        FireDetection.objects.bulk_create(fires)
        return len(fires)
