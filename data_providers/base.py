"""
Base architecture for data providers.
Each provider inherits from BaseDataProvider and implements
search/fetch/normalize/save methods.
"""
import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger("data_providers")


@dataclass
class DataSourceResult:
    source: str
    data: Dict[str, Any]
    fetched_at: datetime
    is_simulated: bool = False
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class ProviderHealth:
    status: str  # "ok", "degraded", "error", "not_configured"
    reason: str = ""
    details: Dict[str, Any] = field(default_factory=dict)


class BaseDataProvider(ABC):
    """
    Abstract base class for all environmental data providers.

    Each provider must implement:
    - name: human-readable provider name
    - source_type: FIRE, CLIMATE, SATELLITE, ATMOSPHERE, WATER, SENSOR
    - health_check(): verify credentials/connectivity
    - search(): find available products/data
    - fetch(): retrieve data from source
    - normalize(): transform to standard format
    - save(): persist to database
    - close(): cleanup resources
    """

    name: str = "BaseProvider"
    source_type: str = "UNKNOWN"
    is_optional: bool = True

    def __init__(self, **kwargs):
        self.demo_mode = kwargs.get("demo_mode", False)
        self.session = None

    @abstractmethod
    def health_check(self) -> ProviderHealth:
        """Check if provider is configured and accessible."""
        ...

    @abstractmethod
    def search(self, **kwargs) -> List[Dict[str, Any]]:
        """Search for available products/data matching criteria."""
        ...

    @abstractmethod
    def fetch(self, **kwargs) -> List[DataSourceResult]:
        """Fetch data from the external source."""
        ...

    def normalize(self, raw_data: Any) -> List[Dict[str, Any]]:
        """Transform raw data into standard format. Override if needed."""
        if isinstance(raw_data, list):
            return raw_data
        return [raw_data] if raw_data else []

    def validate(self, data: Dict[str, Any]) -> bool:
        """Validate data before saving. Override for custom validation."""
        return bool(data)

    @abstractmethod
    def save(self, normalized_data: List[Dict[str, Any]]) -> int:
        """Persist normalized data to database. Returns count of saved items."""
        ...

    def close(self):
        """Cleanup resources."""
        if self.session:
            self.session.close()

    def sync(self, **kwargs) -> Dict[str, Any]:
        """
        Full sync pipeline: health_check → search → fetch → normalize → validate → save.
        Returns summary dict.
        """
        health = self.health_check()
        if health.status != "ok":
            return {"status": "skipped", "reason": health.reason, "provider": self.name}

        try:
            items = self.fetch(**kwargs)
            saved = 0
            for item in items:
                normalized = self.normalize(item)
                for record in normalized:
                    if self.validate(record):
                        self.save([record])
                        saved += 1
            return {"status": "ok", "provider": self.name, "fetched": len(items), "saved": saved}
        except Exception as e:
            logger.error("Sync failed for %s: %s", self.name, str(e))
            return {"status": "error", "provider": self.name, "error": str(e)}

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
