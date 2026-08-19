from decimal import Decimal
from core.services.iez import IEZEngine, IEZCalculator
from .models import IEZCalculation
from django.utils import timezone
import logging

logger = logging.getLogger("apps.iez")


class IEZCalculationService:
    DEFAULT_WEIGHTS = {
        "vegetation": Decimal("0.20"),
        "water": Decimal("0.20"),
        "climate": Decimal("0.15"),
        "fire": Decimal("0.15"),
        "atmosphere": Decimal("0.15"),
        "human_pressure": Decimal("0.05"),
        "vulnerability": Decimal("0.10"),
    }

    def calculate_zone_iez(self, zone, components: dict):
        """Calculate IEZ for a zone from provided components (used by demo data)."""
        engine = IEZEngine()
        decimal_components = {k: Decimal(str(v)) for k, v in components.items()}
        result = engine.compute(decimal_components, self.DEFAULT_WEIGHTS)
        iez = IEZCalculation(
            zone=zone,
            score=float(result["iez"]),
            status=result["level"],
            components=result["components"],
            weights=result["weights"],
            calculated_at=timezone.now(),
            is_simulated=True,
        )
        iez.save()
        zone.current_iez = iez.score
        zone.save(update_fields=["current_iez"])
        return iez

    def calculate_from_real_data(self, zone):
        """Calculate IEZ from real environmental observations."""
        calculator = IEZCalculator()
        return calculator.calculate_zone_iez(zone, self.DEFAULT_WEIGHTS)

    def calculate_all_zones(self, use_real_data=False):
        """Calculate IEZ for all zones."""
        from apps.geography.models import MonitoringZone
        zones = MonitoringZone.objects.all()
        count = 0
        for zone in zones:
            try:
                if use_real_data:
                    self.calculate_from_real_data(zone)
                else:
                    self.calculate_zone_iez(zone, {
                        "vegetation": 70, "water": 60, "climate": 75,
                        "fire": 80, "atmosphere": 70, "human_pressure": 50, "vulnerability": 65,
                    })
                count += 1
            except Exception as e:
                logger.warning("IEZ calculation failed for zone %s: %s", zone.name, str(e))
        return count
