from decimal import Decimal
from typing import Dict, Any, List


class IEZEngine:
    def compute(self, components: Dict[str, Decimal], weights: Dict[str, Decimal]) -> Dict[str, Any]:
        total_weight = Decimal("0")
        weighted_sum = Decimal("0")
        for component, value in components.items():
            weight = weights.get(component, Decimal("0"))
            weighted_sum += value * weight
            total_weight += weight
        if total_weight > 0:
            iez = (weighted_sum / total_weight).quantize(Decimal("0.01"))
        else:
            iez = Decimal("0")
        iez = max(min(iez, Decimal("100")), Decimal("0"))
        level = self._level(iez)
        return {
            "iez": str(iez),
            "level": level,
            "components": {k: str(v) for k, v in components.items()},
            "weights": {k: str(v) for k, v in weights.items()},
        }

    def _level(self, iez: Decimal) -> str:
        if iez >= Decimal("85"):
            return "BON"
        if iez >= Decimal("65"):
            return "VIGILANCE"
        if iez >= Decimal("40"):
            return "DÉGRADÉ"
        return "CRITIQUE"
