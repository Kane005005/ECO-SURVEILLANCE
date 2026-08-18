from decimal import Decimal
from core.services.iez import IEZEngine
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

