from decimal import Decimal
from typing import Dict, Any
from core.services.anomaly import AnomalyEngine


class RiskEngine:
    LEVEL_NORMAL = "NORMAL"
    LEVEL_VIGILANCE = "VIGILANCE"
    LEVEL_HIGH = "HIGH"
    LEVEL_CRITICAL = "CRITICAL"
    LEVEL_LABELS = {
        LEVEL_NORMAL: "Normal",
        LEVEL_VIGILANCE: "Vigilance",
        LEVEL_HIGH: "Risque élevé",
        LEVEL_CRITICAL: "Danger critique",
    }

    def compute(self, anomalies: Dict[str, Any], zone_factors: Dict[str, Decimal]) -> Dict[str, Any]:
        engine = AnomalyEngine()
        risk_score = Decimal("0")
        confidence_score = Decimal("0")
        contributing = []
        for metric, values in anomalies.items():
            result = engine.detect(
                metric=metric,
                current=Decimal(str(values["current"])),
                baseline=Decimal(str(values["baseline"])),
                std_dev=Decimal(str(values["std_dev"])),
            )
            if result.detected:
                risk_score += Decimal(str(abs(result.z_score)))
                confidence_score += Decimal("1")
                contributing.append({"metric": result.metric, "z_score": str(result.z_score), "severity": result.severity})
        max_risk = Decimal("12")
        if risk_score > max_risk:
            risk_score = max_risk
        risk_score = (risk_score / max_risk) * Decimal("100")
        confidence_score = min(confidence_score / Decimal("4"), Decimal("1"))
        level = self._level_from_score(risk_score, confidence_score)
        return {
            "risk_score": str(round(risk_score, 2)),
            "confidence_score": str(round(confidence_score, 2)),
            "level": level,
            "label": self.LEVEL_LABELS[level],
            "contributing_anomalies": contributing,
        }

    def _level_from_score(self, risk_score: Decimal, confidence_score: Decimal) -> str:
        if confidence_score < Decimal("0.4"):
            return self.LEVEL_NORMAL if risk_score < Decimal("40") else self.LEVEL_VIGILANCE
        if risk_score >= Decimal("80") or (risk_score >= Decimal("60") and confidence_score >= Decimal("0.7")):
            return self.LEVEL_CRITICAL
        if risk_score >= Decimal("50"):
            return self.LEVEL_HIGH
        if risk_score >= Decimal("25"):
            return self.LEVEL_VIGILANCE
        return self.LEVEL_NORMAL
