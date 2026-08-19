from celery import shared_task
import logging

logger = logging.getLogger("apps.iez")


@shared_task(bind=True, ignore_result=True)
def compute_all_iez(self):
    """Compute IEZ for all zones from real environmental data."""
    from apps.geography.models import MonitoringZone
    from apps.iez.services import IEZCalculationService
    from django.conf import settings

    service = IEZCalculationService()
    zones = MonitoringZone.objects.all()
    use_real = not getattr(settings, "DEMO_MODE", False)
    count = 0

    for zone in zones:
        try:
            if use_real:
                service.calculate_from_real_data(zone)
            else:
                import random
                components = {
                    "vegetation": round(random.uniform(30, 95), 1),
                    "water": round(random.uniform(25, 90), 1),
                    "climate": round(random.uniform(40, 85), 1),
                    "fire": round(random.uniform(50, 95), 1),
                    "atmosphere": round(random.uniform(40, 80), 1),
                    "human_pressure": round(random.uniform(30, 70), 1),
                    "vulnerability": round(random.uniform(35, 80), 1),
                }
                service.calculate_zone_iez(zone, components)
            count += 1
        except Exception as e:
            logger.warning("IEZ computation failed for zone %s: %s", zone.name, str(e))

    logger.info("IEZ computed for %d zones (real=%s)", count, use_real)
    return {"status": "ok", "zones": count}
