from celery import shared_task
import logging

logger = logging.getLogger("apps.fires")


@shared_task(bind=True, ignore_result=True)
def sync_firms_data(self):
    """Sync fire detection data from NASA FIRMS."""
    from data_providers.firms import FIRMSProvider
    from django.conf import settings

    provider = FIRMSProvider(
        map_key=getattr(settings, "FIRMS_MAP_KEY", ""),
        source=getattr(settings, "FIRMS_SOURCE", "VIIRS"),
        demo_mode=getattr(settings, "DEMO_MODE", False),
    )
    health = provider.health_check()
    if health.status != "ok":
        logger.warning("FIRMS provider not available: %s", health.reason)
        return {"status": "skipped", "reason": health.reason}

    try:
        items = provider.fetch(country="MLI", days=1)
        total_saved = 0
        for item in items:
            normalized = provider.normalize(item)
            saved = provider.save(normalized)
            total_saved += saved
        provider.close()
        logger.info("FIRMS sync complete: %d saved", total_saved)
        return {"status": "ok", "saved": total_saved}
    except Exception as e:
        logger.error("FIRMS sync failed: %s", str(e))
        return {"status": "error", "error": str(e)}
