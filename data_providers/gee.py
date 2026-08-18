from typing import Dict, Any


class GEEProvider:
    name = "Google Earth Engine"
    is_optional = True

    def health_check(self) -> Dict[str, Any]:
        return {"status": "not_implemented", "reason": "Provider non configuré"}

    def close(self) -> None:
        pass
