from typing import Protocol, Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime


@dataclass
class DataSourceResult:
    source: str
    data: Dict[str, Any]
    fetched_at: datetime
    is_simulated: bool = False
    metadata: Optional[Dict[str, Any]] = None


class DataProvider(Protocol):
    name: str
    is_optional: bool = False

    def health_check(self) -> Dict[str, Any]: ...
    def close(self) -> None: ...
