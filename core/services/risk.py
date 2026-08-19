"""
Multi-source Risk Engine.
Computes explainable risk scores from real environmental data.
No opaque AI — all scores are reproducible and traceable.
"""
import logging
from decimal import Decimal
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from datetime import timedelta
from django.utils import timezone

logger = logging.getLogger("apps.risk")


@dataclass
class RiskFactor:
    name: str
    score: float  # 0-100
    weight: float  # 0-1
    value: Any = None
    description: str = ""

    @property
    def weighted_score(self) -> float:
        return self.score * self.weight


@dataclass
class RiskResult:
    risk_score: float  # 0-100
    confidence: float  # 0-1
    level: str  # GREEN, YELLOW, ORANGE, RED
    severity: str  # LOW, MEDIUM, HIGH, CRITICAL
    factors: List[RiskFactor]
    risk_type: str
    algorithm_version: str = "2.0"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "risk_score": round(self.risk_score, 2),
            "confidence": round(self.confidence, 2),
            "level": self.level,
            "severity": self.severity,
            "risk_type": self.risk_type,
            "factors": [
                {"name": f.name, "score": round(f.score, 1), "weight": f.weight,
                 "value": f.value, "description": f.description}
                for f in self.factors
            ],
            "algorithm_version": self.algorithm_version,
        }


class RiskEngine:
    """
    Computes explainable risk scores for different risk types.
    Each risk type has its own weighted formula using real data signals.
    """

    # Risk type definitions with weights for each contributing factor
    RISK_PROFILES = {
        "WILDFIRE": {
            "factors": {
                "fire_detections": {"weight": 0.30, "description": "Feux actifs FIRMS"},
                "temperature": {"weight": 0.15, "description": "Température élevée"},
                "wind_speed": {"weight": 0.10, "description": "Vent favorisant propagation"},
                "humidity": {"weight": 0.15, "description": "Faible humidité"},
                "precipitation": {"weight": 0.10, "description": "Déficit pluviométrique"},
                "vegetation_dryness": {"weight": 0.15, "description": "Végétation sèche (NDVI/NDMI)"},
                "anomaly_score": {"weight": 0.05, "description": "Anomalies environnementales"},
            },
        },
        "DROUGHT": {
            "factors": {
                "precipitation_deficit": {"weight": 0.35, "description": "Déficit pluviométrique"},
                "temperature_anomaly": {"weight": 0.20, "description": "Température au-dessus de la normale"},
                "humidity_deficit": {"weight": 0.15, "description": "Humidité basse"},
                "vegetation_stress": {"weight": 0.15, "description": "Stress végétal (NDVI)"},
                "water_level": {"weight": 0.15, "description": "Niveau bas des cours d'eau"},
            },
        },
        "VEGETATION_DEGRADATION": {
            "factors": {
                "ndvi_decline": {"weight": 0.35, "description": "Baisse NDVI significative"},
                "nbr_change": {"weight": 0.20, "description": "Changement NBR"},
                "fire_impact": {"weight": 0.20, "description": "Impact incendie"},
                "precipitation": {"weight": 0.15, "description": "Précipitations"},
                "human_pressure": {"weight": 0.10, "description": "Pression anthropique"},
            },
        },
        "WATER_POLLUTION": {
            "factors": {
                "ph_anomaly": {"weight": 0.25, "description": "pH anormal"},
                "turbidity": {"weight": 0.25, "description": "Turbidité élevée"},
                "dissolved_oxygen": {"weight": 0.25, "description": "Oxygène dissous bas"},
                "conductivity": {"weight": 0.15, "description": "Conductivité anormale"},
                "temperature": {"weight": 0.10, "description": "Température eau"},
            },
        },
        "WATER_STRESS": {
            "factors": {
                "water_level": {"weight": 0.35, "description": "Niveau bas"},
                "precipitation_deficit": {"weight": 0.30, "description": "Manque de pluie"},
                "temperature_high": {"weight": 0.20, "description": "Évaporation accrue"},
                "vegetation_stress": {"weight": 0.15, "description": "Stress végétal"},
            },
        },
        "HEAT": {
            "factors": {
                "temperature_anomaly": {"weight": 0.40, "description": "Température extrême"},
                "heat_duration": {"weight": 0.20, "description": "Durée canicule"},
                "humidity": {"weight": 0.15, "description": "Stress thermique"},
                "fire_risk": {"weight": 0.15, "description": "Risque incendie lié"},
                "vulnerability": {"weight": 0.10, "description": "Vulnérabilité zone"},
            },
        },
        "ATMOSPHERIC_ANOMALY": {
            "factors": {
                "aerosol_index": {"weight": 0.30, "description": "Indice aérosols"},
                "so2_level": {"weight": 0.25, "description": "SO2 élevé"},
                "o3_level": {"weight": 0.25, "description": "O3 anormal"},
                "no2_level": {"weight": 0.20, "description": "NO2 élevé"},
            },
        },
    }

    def compute(self, risk_type: str, zone_signals: Dict[str, float],
                anomalies: Optional[Dict[str, Any]] = None) -> RiskResult:
        """
        Compute risk score for a given type.

        risk_type: WILDFIRE, DROUGHT, etc.
        zone_signals: {"fire_detections": 0-100, "temperature": 0-100, ...}
            Each value is a normalized 0-100 risk indicator.
        anomalies: optional anomaly data to factor in
        """
        profile = self.RISK_PROFILES.get(risk_type)
        if not profile:
            return RiskResult(
                risk_score=0, confidence=0, level="GREEN", severity="LOW",
                factors=[], risk_type=risk_type
            )

        factors = []
        total_weight = 0
        weighted_sum = 0

        for factor_name, factor_config in profile["factors"].items():
            weight = factor_config["weight"]
            value = zone_signals.get(factor_name, 50.0)  # Default neutral if missing
            value = max(0, min(100, value))

            factors.append(RiskFactor(
                name=factor_name,
                score=value,
                weight=weight,
                value=value,
                description=factor_config["description"],
            ))
            weighted_sum += value * weight
            total_weight += weight

        # Add anomaly boost if present
        if anomalies:
            anomaly_score = anomalies.get("max_severity_score", 0)
            if anomaly_score > 0:
                anomaly_boost = min(anomaly_score * 0.1, 10)  # Max 10 points boost
                weighted_sum += anomaly_boost
                factors.append(RiskFactor(
                    name="anomaly_boost",
                    score=anomaly_boost / 0.05,  # Normalize
                    weight=0.05,
                    value=anomaly_boost,
                    description="Boost des anomalies détectées",
                ))
                total_weight += 0.05

        risk_score = weighted_sum / max(total_weight, 0.01) if total_weight > 0 else 0
        risk_score = max(0, min(100, risk_score))

        # Confidence based on how many factors have real data
        real_data_count = sum(1 for f in factors if f.value != 50.0)
        confidence = real_data_count / max(len(factors), 1)

        level = self._score_to_level(risk_score)
        severity = self._level_to_severity(level)

        return RiskResult(
            risk_score=risk_score,
            confidence=confidence,
            level=level,
            severity=severity,
            factors=factors,
            risk_type=risk_type,
        )

    def compute_fire_risk(self, zone) -> RiskResult:
        """Compute fire risk for a zone using real data signals."""
        from apps.fires.models import FireDetection
        from apps.climate.models import ClimateObservation
        from apps.vegetation.models import VegetationObservation

        now = timezone.now()
        signals = {}

        # Fire detections (last 7 days)
        fire_count = FireDetection.objects.filter(
            zone=zone, detected_at__gte=now - timedelta(days=7)
        ).count()
        signals["fire_detections"] = min(fire_count * 10, 100)  # 10 fires → 100

        # Temperature
        recent_temp = ClimateObservation.objects.filter(
            zone=zone, variable="TEMPERATURE", observed_at__gte=now - timedelta(days=3)
        ).values_list("value", flat=True)
        if recent_temp:
            avg_temp = sum(recent_temp) / len(recent_temp)
            signals["temperature"] = min(max((avg_temp - 25) * 5, 0), 100)  # 25°C → 0, 45°C → 100

        # Humidity
        recent_hum = ClimateObservation.objects.filter(
            zone=zone, variable="HUMIDITY", observed_at__gte=now - timedelta(days=3)
        ).values_list("value", flat=True)
        if recent_hum:
            avg_hum = sum(recent_hum) / len(recent_hum)
            signals["humidity"] = min(max((80 - avg_hum) * 2, 0), 100)  # 80% → 0, 30% → 100

        # Precipitation
        recent_precip = ClimateObservation.objects.filter(
            zone=zone, variable="PRECIPITATION", observed_at__gte=now - timedelta(days=7)
        ).values_list("value", flat=True)
        if recent_precip:
            total_precip = sum(recent_precip)
            signals["precipitation"] = min(max((50 - total_precip) * 2, 0), 100)

        # NDVI / vegetation dryness
        recent_ndvi = VegetationObservation.objects.filter(
            zone=zone, index_name="NDVI", acquisition_date__gte=(now - timedelta(days=14)).date()
        ).values_list("value", flat=True)
        if recent_ndvi:
            avg_ndvi = sum(recent_ndvi) / len(recent_ndvi)
            signals["vegetation_dryness"] = min(max((0.6 - avg_ndvi) * 200, 0), 100)

        return self.compute("WILDFIRE", signals)

    def compute_drought_risk(self, zone) -> RiskResult:
        """Compute drought risk for a zone."""
        from apps.climate.models import ClimateObservation
        from apps.vegetation.models import VegetationObservation
        from apps.water.models import WaterObservation

        now = timezone.now()
        signals = {}

        # Precipitation deficit (30-day)
        recent_precip = ClimateObservation.objects.filter(
            zone=zone, variable="PRECIPITATION",
            observed_at__gte=now - timedelta(days=30)
        ).values_list("value", flat=True)
        if recent_precip:
            total = sum(recent_precip)
            signals["precipitation_deficit"] = min(max((150 - total) * 1.5, 0), 100)

        # Temperature anomaly
        recent_temp = ClimateObservation.objects.filter(
            zone=zone, variable="TEMPERATURE",
            observed_at__gte=now - timedelta(days=7)
        ).values_list("value", flat=True)
        if recent_temp:
            avg = sum(recent_temp) / len(recent_temp)
            signals["temperature_anomaly"] = min(max((avg - 30) * 8, 0), 100)

        # Humidity
        recent_hum = ClimateObservation.objects.filter(
            zone=zone, variable="HUMIDITY",
            observed_at__gte=now - timedelta(days=7)
        ).values_list("value", flat=True)
        if recent_hum:
            avg = sum(recent_hum) / len(recent_hum)
            signals["humidity_deficit"] = min(max((70 - avg) * 3, 0), 100)

        # Vegetation stress
        recent_ndvi = VegetationObservation.objects.filter(
            zone=zone, index_name="NDVI",
            acquisition_date__gte=(now - timedelta(days=14)).date()
        ).values_list("value", flat=True)
        if recent_ndvi:
            avg = sum(recent_ndvi) / len(recent_ndvi)
            signals["vegetation_stress"] = min(max((0.5 - avg) * 200, 0), 100)

        # Water level
        recent_water = WaterObservation.objects.filter(
            water_body__zone=zone, metric="WATER_LEVEL",
            measured_at__gte=now - timedelta(days=7)
        ).values_list("value", flat=True)
        if recent_water:
            avg = sum(recent_water) / len(recent_water)
            signals["water_level"] = min(max((3 - avg) * 50, 0), 100)

        return self.compute("DROUGHT", signals)

    def compute_all_risks(self, zone) -> List[RiskResult]:
        """Compute all risk types for a zone."""
        results = []
        for risk_type in self.RISK_PROFILES:
            method_name = f"compute_{risk_type.lower()}_risk"
            method = getattr(self, method_name, None)
            if method:
                try:
                    results.append(method(zone))
                except Exception as e:
                    logger.warning("Risk computation failed for %s on zone %s: %s", risk_type, zone.name, str(e))
        return results

    def _score_to_level(self, score: float) -> str:
        if score >= 80:
            return "RED"
        if score >= 50:
            return "ORANGE"
        if score >= 25:
            return "YELLOW"
        return "GREEN"

    def _level_to_severity(self, level: str) -> str:
        return {"RED": "CRITICAL", "ORANGE": "HIGH", "YELLOW": "MEDIUM", "GREEN": "LOW"}.get(level, "LOW")
