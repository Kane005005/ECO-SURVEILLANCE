"""
IEZ (Indice Environnemental de Zone) Engine.
Computes a 0-100 environmental quality score for each monitoring zone.
Aggregates 7 dimensions with configurable weights.
"""
import logging
from decimal import Decimal
from typing import Dict, Any, Optional
from datetime import timedelta
from django.utils import timezone

logger = logging.getLogger("apps.iez")


class IEZEngine:
    """
    Computes IEZ from weighted environmental dimensions.
    Each dimension score is 0-100 (0 = critical, 100 = excellent).
    """

    # Default weights — must sum to 1.0
    DEFAULT_WEIGHTS = {
        "vegetation": Decimal("0.20"),
        "water": Decimal("0.20"),
        "climate": Decimal("0.15"),
        "fire": Decimal("0.15"),
        "atmosphere": Decimal("0.15"),
        "human_pressure": Decimal("0.05"),
        "vulnerability": Decimal("0.10"),
    }

    def compute(self, components: Dict[str, Decimal], weights: Dict[str, Decimal] = None) -> Dict[str, Any]:
        """Compute IEZ from component scores and weights."""
        if weights is None:
            weights = self.DEFAULT_WEIGHTS

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


class IEZCalculator:
    """
    Calculates IEZ from real environmental data for a zone.
    Each dimension is scored independently from actual observations.
    """

    def calculate_zone_iez(self, zone, weights: Dict[str, Decimal] = None) -> Dict[str, Any]:
        """Calculate IEZ for a zone from its real data."""
        from apps.vegetation.models import VegetationObservation
        from apps.climate.models import ClimateObservation
        from apps.water.models import WaterObservation
        from apps.atmosphere.models import AtmosphericObservation
        from apps.fires.models import FireDetection
        from apps.anomalies.models import Anomaly

        engine = IEZEngine()
        now = timezone.now()
        components = {}

        # 1. Vegetation score (NDVI-based)
        veg_obs = VegetationObservation.objects.filter(
            zone=zone, index_name="NDVI",
            acquisition_date__gte=(now - timedelta(days=14)).date()
        ).values_list("value", flat=True)
        if veg_obs:
            avg_ndvi = sum(veg_obs) / len(veg_obs)
            # NDVI 0.8 → 100, 0.4 → 50, 0.0 → 0
            components["vegetation"] = max(0, min(100, avg_ndvi * 125))
        else:
            components["vegetation"] = Decimal("50")  # Neutral if no data

        # 2. Water score (multi-metric)
        water_scores = []
        for metric, good_range in [
            ("PH", (6.5, 8.5)),
            ("DISSOLVED_OXYGEN", (5.0, 100)),
            ("TURBIDITY", (0, 50)),
        ]:
            water_vals = WaterObservation.objects.filter(
                water_body__zone=zone, metric=metric,
                measured_at__gte=now - timedelta(days=14)
            ).values_list("value", flat=True)
            if water_vals:
                avg = sum(water_vals) / len(water_vals)
                lo, hi = good_range
                if lo <= avg <= hi:
                    water_scores.append(100)
                else:
                    dist = min(abs(avg - lo), abs(avg - hi))
                    water_scores.append(max(0, 100 - dist * 10))

        if water_scores:
            components["water"] = sum(water_scores) / len(water_scores)
        else:
            components["water"] = Decimal("50")

        # 3. Climate score
        temp_vals = ClimateObservation.objects.filter(
            zone=zone, variable="TEMPERATURE",
            observed_at__gte=now - timedelta(days=7)
        ).values_list("value", flat=True)
        precip_vals = ClimateObservation.objects.filter(
            zone=zone, variable="PRECIPITATION",
            observed_at__gte=now - timedelta(days=30)
        ).values_list("value", flat=True)

        climate_score = Decimal("50")
        if temp_vals:
            avg_temp = sum(temp_vals) / len(temp_vals)
            # 25-35°C is normal for Mali → good
            if 25 <= avg_temp <= 35:
                temp_score = 100
            elif avg_temp > 45:
                temp_score = 20
            else:
                temp_score = 60
            climate_score = Decimal(str(temp_score))

        if precip_vals:
            total_precip = sum(precip_vals)
            # 50-200mm/month is adequate for Mali
            if total_precip >= 50:
                precip_bonus = min(total_precip / 5, 30)
                climate_score = min(climate_score + Decimal(str(precip_bonus)), Decimal("100"))

        components["climate"] = climate_score

        # 4. Fire score (inverse: fewer fires = better)
        fire_count = FireDetection.objects.filter(
            zone=zone, detected_at__gte=now - timedelta(days=14)
        ).count()
        # 0 fires → 100, 5 fires → 50, 10+ fires → 0
        components["fire"] = max(0, min(100, 100 - fire_count * 10))

        # 5. Atmosphere score
        atmo_obs = AtmosphericObservation.objects.filter(
            zone=zone, observed_at__gte=now - timedelta(days=7)
        ).values_list("value", flat=True)
        if atmo_obs:
            avg_atmo = sum(atmo_obs) / len(atmo_obs)
            # Low values are good for pollution
            components["atmosphere"] = max(0, min(100, 100 - avg_atmo * 100))
        else:
            components["atmosphere"] = Decimal("50")

        # 6. Human pressure (based on zone vulnerability + anomalies)
        vuln_map = {"LOW": 90, "MEDIUM": 65, "HIGH": 35, "CRITICAL": 10}
        components["human_pressure"] = vuln_map.get(zone.vulnerability_level, 50)

        # 7. Vulnerability (inverse of current anomaly count)
        anomaly_count = Anomaly.objects.filter(
            zone=zone, detected_at__gte=now - timedelta(days=14)
        ).exclude(status="RESOLVED").count()
        components["vulnerability"] = max(0, min(100, 100 - anomaly_count * 15))

        # Compute weighted IEZ
        result = engine.compute(components, weights)

        # Save to database
        from apps.iez.models import IEZCalculation
        iez_calc = IEZCalculation(
            zone=zone,
            score=float(result["iez"]),
            status=result["level"],
            components=result["components"],
            weights=result["weights"],
            calculated_at=now,
            is_simulated=False,
        )
        iez_calc.save()

        # Update zone's current IEZ
        zone.current_iez = iez_calc.score
        zone.save(update_fields=["current_iez"])

        return result
