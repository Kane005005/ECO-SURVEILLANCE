"""
Google Flood Hub Data Provider (Passif / Préparatoire).
Architecture préméditée pour l'ingestion des prévisions hydrologiques Google Flood Hub
dès l'ouverture publique complète de l'API / attribution des clés.
"""
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from decouple import config

from data_providers.base import BaseDataProvider, DataSourceResult, ProviderHealth

logger = logging.getLogger("data_providers")


class FloodHubProvider(BaseDataProvider):
    name = "Google Flood Hub"
    source_type = "WATER"
    is_optional = True

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.api_key = kwargs.get("api_key") or config("FLOOD_HUB_API_KEY", default="")
        self.base_url = kwargs.get("base_url") or "https://floodhub.googleapis.com/v1"

    def health_check(self) -> ProviderHealth:
        if not self.api_key:
            return ProviderHealth(
                status="not_configured",
                reason="FLOOD_HUB_API_KEY non configuré (Intégration préparatoire Google Flood Hub)",
                details={"mode": "preparatory_passive", "base_url": self.base_url},
            )
        return ProviderHealth(
            status="ok",
            reason="Google Flood Hub configuré",
            details={"base_url": self.base_url},
        )

    def search(self, **kwargs) -> List[Dict[str, Any]]:
        """Recherche de jaugeages Flood Hub disponibles pour le Mali."""
        return [
            {
                "country": "ML",
                "provider": self.name,
                "status": "ready_for_activation",
            }
        ]

    def fetch(self, **kwargs) -> List[DataSourceResult]:
        """Fetch bouchon préparatoire ne bloquant pas le système."""
        logger.info("FloodHubProvider en attente d'activation de clé API dédiée.")
        return []

    def normalize(self, raw_data: Any) -> List[Dict[str, Any]]:
        return []

    def save(self, normalized_data: List[Dict[str, Any]]) -> int:
        return 0
