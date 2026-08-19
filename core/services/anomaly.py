"""
Enhanced Anomaly Detection Engine.
Supports z-score, IQR, and multi-signal detection across all data sources.
"""
import logging
from typing import Dict, Any, List, Optional, Tuple
from decimal import Decimal
from dataclasses import dataclass
from datetime import timedelta
from django.utils import timezone

logger = logging.getLogger("apps.anomalies")


@dataclass
class AnomalyResult:
    detected: bool
    metric: str
    z_score: Decimal
    severity: str  # NONE, LOW, MEDIUM, HIGH, CRITICAL
    details: Dict[str, Any]


class AnomalyEngine:
    """
    Multi-method anomaly detection engine.

    Severity thresholds (z-score based):
        |z| < 1.5  → NONE (normal)
        1.5 ≤ |z| < 2.5 → LOW
        2.5 ≤ |z| < 4.0 → MEDIUM
        |z| ≥ 4.0 → HIGH
        |z| ≥ 6.0 → CRITICAL
    """

    THRESHOLDS = {
        "LOW": Decimal("1.5"),
        "MEDIUM": Decimal("2.5"),
        "HIGH": Decimal("4.0"),
        "CRITICAL": Decimal("6.0"),
    }

    def detect(self, metric: str, current: Decimal, baseline: Decimal,
               std_dev: Decimal) -> AnomalyResult:
        """Detect anomaly using z-score method."""
        if std_dev <= 0:
            return AnomalyResult(
                detected=False, metric=metric, z_score=Decimal("0"),
                severity="NONE", details={}
            )

        z_score = (current - baseline) / std_dev
        severity = self._severity_from_zscore(z_score)

        return AnomalyResult(
            detected=severity != "NONE",
            metric=metric,
            z_score=z_score,
            severity=severity,
            details={
                "current": str(current),
                "baseline": str(baseline),
                "std_dev": str(std_dev),
                "method": "z_score",
            },
        )

    def detect_directional(self, metric: str, current: Decimal, baseline: Decimal,
                           std_dev: Decimal, direction: str = "any") -> AnomalyResult:
        """
        Detect anomaly with directional awareness.
        direction: 'above', 'below', or 'any'
        Useful for:
        - NDVI: only 'below' is anomaly (vegetation loss)
        - Temperature: 'above' is heat anomaly
        - Precipitation: 'below' is drought
        """
        result = self.detect(metric, current, baseline, std_dev)
        if not result.detected:
            return result

        z = result.z_score
        if direction == "above" and z < 0:
            return AnomalyResult(detected=False, metric=metric, z_score=z, severity="NONE", details={})
        if direction == "below" and z > 0:
            return AnomalyResult(detected=False, metric=metric, z_score=z, severity="NONE", details={})

        return result

    def detect_multi_signal(self, signals: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Detect anomalies from multiple signals simultaneously.
        signals: [{"metric": str, "current": float, "baseline": float, "std_dev": float, "direction": str}]

        Returns aggregated anomaly assessment.
        """
        results = []
        max_severity = "NONE"
        severity_order = ["NONE", "LOW", "MEDIUM", "HIGH", "CRITICAL"]

        for signal in signals:
            direction = signal.get("direction", "any")
            result = self.detect_directional(
                metric=signal["metric"],
                current=Decimal(str(signal["current"])),
                baseline=Decimal(str(signal["baseline"])),
                std_dev=Decimal(str(signal["std_dev"])),
                direction=direction,
            )
            results.append(result)
            if severity_order.index(result.severity) > severity_order.index(max_severity):
                max_severity = result.severity

        detected_count = sum(1 for r in results if r.detected)
        avg_z_score = sum(abs(r.z_score) for r in results) / max(len(results), 1)

        return {
            "detected": detected_count > 0,
            "max_severity": max_severity,
            "detected_count": detected_count,
            "total_signals": len(results),
            "avg_z_score": float(avg_z_score),
            "results": [
                {
                    "metric": r.metric,
                    "detected": r.detected,
                    "z_score": float(r.z_score),
                    "severity": r.severity,
                }
                for r in results
            ],
        }

    def compute_baseline_stats(self, values: List[float]) -> Tuple[float, float]:
        """Compute mean and std_dev from a list of values."""
        import statistics
        if len(values) < 3:
            return (0, 0)
        mean = statistics.mean(values)
        stdev = statistics.stdev(values) if len(values) > 1 else 0
        return (mean, stdev)

    def _severity_from_zscore(self, z_score: Decimal) -> str:
        abs_z = abs(z_score)
        if abs_z >= self.THRESHOLDS["CRITICAL"]:
            return "CRITICAL"
        if abs_z >= self.THRESHOLDS["HIGH"]:
            return "HIGH"
        if abs_z >= self.THRESHOLDS["MEDIUM"]:
            return "MEDIUM"
        if abs_z >= self.THRESHOLDS["LOW"]:
            return "LOW"
        return "NONE"


class ZoneAnomalyScanner:
    """
    Scans all recent observations for a zone and detects anomalies
    across all data sources: vegetation, climate, water, atmosphere, fire.
    """

    def scan_zone(self, zone) -> List[Dict[str, Any]]:
        """Run full anomaly scan for a zone. Returns list of detected anomalies."""
        from apps.vegetation.models import VegetationObservation
        from apps.climate.models import ClimateObservation
        from apps.water.models import WaterObservation
        from apps.atmosphere.models import AtmosphericObservation
        from apps.fires.models import FireDetection

        engine = AnomalyEngine()
        anomalies = []

        # Vegetation anomalies (NDVI only — only 'below' is anomaly)
        anomalies.extend(self._scan_observations(
            zone, VegetationObservation, "acquisition_date", "VEGETATION",
            engine, field_map={"value": "value", "baseline": "baseline_value", "std": "std_dev"},
            direction="below",
        ))

        # Climate anomalies
        for var in ["TEMPERATURE", "PRECIPITATION", "HUMIDITY", "WIND_SPEED"]:
            anomalies.extend(self._scan_observations(
                zone, ClimateObservation, "observed_at", "CLIMATE",
                engine, field_map={"value": "value", "baseline": "baseline_value", "std": "std_dev"},
                variable_filter=var,
                direction="below" if var == "PRECIPITATION" else "above" if var == "TEMPERATURE" else "any",
            ))

        # Atmosphere anomalies
        for var in ["SO2", "O3", "AEROSOLS", "NO2"]:
            anomalies.extend(self._scan_observations(
                zone, AtmosphericObservation, "observed_at", "ATMOSPHERE",
                engine, field_map={"value": "value", "baseline": "baseline_value", "std": "std_dev"},
                variable_filter=var,
                direction="above",
            ))

        # Fire anomalies (sudden increase)
        fire_count_recent = FireDetection.objects.filter(
            zone=zone, detected_at__gte=timezone.now() - timedelta(days=7)
        ).count()
        fire_count_baseline = FireDetection.objects.filter(
            zone=zone,
            detected_at__gte=timezone.now() - timedelta(days=37),
            detected_at__lt=timezone.now() - timedelta(days=7),
        ).count()
        if fire_count_baseline > 0 and fire_count_recent > fire_count_baseline * 2:
            anomalies.append({
                "anomaly_type": "FIRE",
                "zone": zone,
                "source": "AnomalyEngine",
                "severity": "HIGH" if fire_count_recent > fire_count_baseline * 3 else "MEDIUM",
                "metric": "fire_count_7d",
                "current_value": float(fire_count_recent),
                "baseline_value": float(fire_count_baseline),
                "description": f"Augmentation des feux: {fire_count_recent} cette semaine vs {fire_count_baseline} baseline",
                "is_simulated": False,
            })

        return anomalies

    def _scan_observations(self, zone, model_class, date_field, anomaly_type, engine,
                           field_map, variable_filter=None, direction="any"):
        """Generic observation scanner for any model."""
        from django.utils import timezone as tz

        qs = model_class.objects.filter(zone=zone).order_by(f"-{date_field}")[:100]
        if variable_filter:
            if hasattr(model_class, 'variable'):
                qs = qs.filter(variable=variable_filter)
            elif hasattr(model_class, 'index_name'):
                qs = qs.filter(index_name=variable_filter)

        observations = list(qs)
        if len(observations) < 3:
            return []

        values = []
        baselines = []
        stds = []
        for obs in observations:
            val = getattr(obs, field_map["value"], None)
            bl = getattr(obs, field_map["baseline"], None)
            std = getattr(obs, field_map["std"], None)
            if val is not None and bl is not None and std is not None and std > 0:
                values.append(float(val))
                baselines.append(float(bl))
                stds.append(float(std))

        if not values:
            return []

        import statistics
        mean_val = statistics.mean(values)
        mean_bl = statistics.mean(baselines)
        mean_std = statistics.mean(stds)

        current_obs = observations[0]
        current_val = getattr(current_obs, field_map["value"], None)
        if current_val is None:
            return []

        metric_name = variable_filter or getattr(current_obs, 'index_name', 'unknown')
        result = engine.detect_directional(
            metric=metric_name,
            current=Decimal(str(current_val)),
            baseline=Decimal(str(mean_bl)),
            std_dev=Decimal(str(mean_std)),
            direction=direction,
        )

        if not result.detected:
            return []

        return [{
            "anomaly_type": anomaly_type,
            "zone": zone,
            "source": "AnomalyEngine",
            "severity": result.severity,
            "metric": metric_name,
            "current_value": float(current_val),
            "baseline_value": mean_bl,
            "z_score": float(result.z_score),
            "description": f"{metric_name}: {current_val} vs baseline {mean_bl:.3f} (z={float(result.z_score):.2f})",
            "is_simulated": getattr(current_obs, 'is_simulated', False),
        }]
