from typing import Dict, Any
from decimal import Decimal


class AnomalyResult:
    def __init__(self, detected: bool, metric: str, z_score: Decimal, severity: str, details: Dict[str, Any]):
        self.detected = detected
        self.metric = metric
        self.z_score = z_score
        self.severity = severity
        self.details = details


class AnomalyEngine:
    def detect(self, metric: str, current: Decimal, baseline: Decimal, std_dev: Decimal) -> AnomalyResult:
        if std_dev <= 0:
            return AnomalyResult(detected=False, metric=metric, z_score=Decimal("0"), severity="NONE", details={})
        z_score = (current - baseline) / std_dev
        if abs(z_score) < 1.5:
            severity = "NONE"
        elif abs(z_score) < 2.5:
            severity = "LOW"
        elif abs(z_score) < 4.0:
            severity = "MEDIUM"
        else:
            severity = "HIGH"
        return AnomalyResult(
            detected=abs(z_score) >= 1.5,
            metric=metric, z_score=z_score, severity=severity,
            details={"current": str(current), "baseline": str(baseline), "std_dev": str(std_dev)},
        )
