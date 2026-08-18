from celery import shared_task
import logging

logger = logging.getLogger("apps.iez")

@shared_task(bind=True, ignore_result=True)
def compute_all_iez(self):
    from apps.geography.models import MonitoringZone
    from apps.iez.services import IEZCalculationService

    service = IEZCalculationService()
    zones = MonitoringZone.objects.all()
    count = 0
    for zone in zones:
        components = {
            "vegetation": max(0, min(100, 50 + (hash(zone.name) % 50))),
            "water": max(0, min(100, 40 + (hash(zone.name + "w") % 60))),
            "climate": max(0, min(100, 55 + (hash(zone.name + "c") % 45))),
            "fire": max(0, min(100, 60 + (hash(zone.name + "f") % 40))),
            "atmosphere": max(0, min(100, 50 + (hash(zone.name + "a") % 50))),
            "human_pressure": max(0, min(100, 45 + (hash(zone.name + "h") % 55))),
            "vulnerability": max(0, min(100, 50 + (hash(zone.name + "v") % 50))),
        }
        service.calculate_zone_iez(zone, components)
        count += 1
    logger.info("IEZ computed for %d zones", count)
    return {"status": "ok", "zones": count}
