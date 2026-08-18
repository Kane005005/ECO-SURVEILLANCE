from typing import Protocol, Dict, Any


class AIProvider(Protocol):
    name: str
    is_optional: bool = True

    def health_check(self) -> Dict[str, Any]: ...
    def close(self) -> None: ...
