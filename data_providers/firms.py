from .base import DataProvider
from typing import Dict, Any, List, Optional
import requests


class FIRMSProvider(DataProvider):
    name = "NASA FIRMS"
    is_optional = False

    def __init__(self, map_key: Optional[str] = None, source: str = "MODIS, VIIRS"):
        self.map_key = map_key
        self.source = source
        self.session = requests.Session()

    def health_check(self) -> Dict[str, Any]:
        if not self.map_key:
            return {"status": "degraded", "reason": "FIRMS_MAP_KEY manquant"}
        return {"status": "ok"}

    def close(self) -> None:
        self.session.close()

    def fetch_active_fires(self, bbox=None, country="MLI", days=1) -> List[Dict[str, Any]]:
        base_url = "https://firms.modaps.eosdis.nasa.gov/api/active_fire"
        endpoint = f"{base_url}/{self.source}/json/{self.map_key}/{days}/{country}"
        if bbox:
            endpoint += f"/{bbox['min_lon']},{bbox['min_lat']},{bbox['max_lon']},{bbox['max_lat']}"
        response = self.session.get(endpoint, timeout=30)
        response.raise_for_status()
        return response.json()
