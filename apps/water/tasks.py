"""
Celery tasks for Hydrology and Flood Monitoring.
Syncs GloFAS river discharge forecasts and NASA LANCE Flood observations.
"""
from celery import shared_task
import logging
from django.conf import settings

logger = logging.getLogger("apps.water")


@shared_task(bind=True, ignore_result=True)
def sync_glofas_hydrology(self, date=None):
    """Sync Copernicus GloFAS hydrology forecasts for Mali stations."""
    from data_providers.glofas import GloFASProvider

    provider = GloFASProvider(
        cds_url=getattr(settings, "CDS_API_URL", "https://ewds.climate.copernicus.eu/api"),
        cds_key=getattr(settings, "CDS_API_KEY", ""),
        demo_mode=getattr(settings, "DEMO_MODE", False),
    )
    health = provider.health_check()
    if health.status not in ["ok"]:
        logger.warning("GloFAS provider status: %s (%s)", health.status, health.reason)

    try:
        items = provider.fetch(date=date)
        saved = provider.save(provider.normalize(items))
        provider.close()
        logger.info("GloFAS hydrology sync complete: %d forecasts saved.", saved)
        return {"status": "ok", "saved": saved}
    except Exception as e:
        logger.error("GloFAS hydrology sync failed: %s", str(e))
        return {"status": "error", "error": str(e)}


@shared_task(bind=True, ignore_result=True)
def sync_lance_flood(self, date=None):
    """Sync NASA LANCE Flood VIIRS NRT3 observations for Mali tiles."""
    from data_providers.lance_flood import LANCEFloodProvider

    provider = LANCEFloodProvider(
        earthdata_token=getattr(settings, "EARTHDATA_TOKEN", ""),
        base_url=getattr(settings, "LANCE_FLOOD_BASE_URL", "https://nrt3.modaps.eosdis.nasa.gov/archive/allData/5200/VCDWD_L3_F2_NRT/Recent"),
        demo_mode=getattr(settings, "DEMO_MODE", False),
    )
    health = provider.health_check()
    if health.status not in ["ok"]:
        logger.warning("NASA LANCE Flood provider status: %s (%s)", health.status, health.reason)

    try:
        items = provider.fetch(date=date)
        saved = provider.save(provider.normalize(items))
        provider.close()
        logger.info("NASA LANCE Flood sync complete: %d observations saved.", saved)
        return {"status": "ok", "saved": saved}
    except Exception as e:
        logger.error("NASA LANCE Flood sync failed: %s", str(e))
        return {"status": "error", "error": str(e)}
