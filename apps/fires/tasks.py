from celery import shared_task
import logging

logger = logging.getLogger("apps.fires")

@shared_task(bind=True, ignore_result=True)
def sync_firms_data(self):
    logger.info("Sync FIRMS data task triggered")
    from data_providers.firms import FIRMSProvider
    from django.conf import settings
    provider = FIRMSProvider(map_key=getattr(settings, "FIRMS_MAP_KEY", ""))
    health = provider.health_check()
    if health.get("status") != "ok":
        logger.warning("FIRMS provider not available: %s", health)
        return {"status": "skipped", "reason": health.get("reason", "unknown")}
    try:
        data = provider.fetch_active_fires(country="MLI", days=1)
        provider.close()
        logger.info("FIRMS sync completed, received %d items", len(data) if isinstance(data, list) else 0)
        return {"status": "ok", "count": len(data) if isinstance(data, list) else 0}
    except Exception as e:
        logger.error("FIRMS sync failed: %s", str(e))
        return {"status": "error", "error": str(e)}
