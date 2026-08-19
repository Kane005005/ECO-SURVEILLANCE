from celery import shared_task
import logging
from datetime import timedelta

logger = logging.getLogger("apps.climate")


@shared_task(bind=True, ignore_result=True)
def sync_nasa_power(self):
    """Sync climate data from NASA POWER for all zones.
    Uses 7-3 days ago window (POWER has ~2 day lag)."""
    from apps.geography.models import MonitoringZone
    from data_providers.nasa_power import NASAPowerProvider
    from django.utils import timezone

    provider = NASAPowerProvider()
    health = provider.health_check()
    if health.status != "ok":
        logger.warning("NASA POWER provider not available: %s", health.reason)
        return {"status": "skipped", "reason": health.reason}

    zones = MonitoringZone.objects.exclude(latitude__isnull=True).exclude(longitude__isnull=True)
    total_saved = 0

    # POWER has ~2 day lag; fetch from 7 days ago to 3 days ago
    end = (timezone.now() - timedelta(days=3)).strftime("%Y%m%d")
    start = (timezone.now() - timedelta(days=7)).strftime("%Y%m%d")

    for zone in zones:
        try:
            results = provider.fetch(
                latitude=zone.latitude,
                longitude=zone.longitude,
                start_date=start,
                end_date=end,
            )
            for result in results:
                normalized = provider.normalize(result)
                saved = provider.save(normalized)
                total_saved += saved
        except Exception as e:
            logger.warning("POWER sync failed for zone %s: %s", zone.name, str(e))

    provider.close()
    logger.info("NASA POWER sync complete: %d observations saved", total_saved)
    return {"status": "ok", "saved": total_saved}
