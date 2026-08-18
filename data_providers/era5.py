from typing import Dict, Any


class ERA5Provider:
    name = "ERA5"
    is_optional = True

    def health_check(self) -> Dict[str, Any]:
        return {"status": "not_implemented", "reason": "Provider non configuré"}

    def close(self) -> None:
        pass
