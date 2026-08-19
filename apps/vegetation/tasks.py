"""
Celery tasks for Sentinel-2 vegetation data sync.
"""
from celery import shared_task
from celery.utils.log import get_task_logger

logger = get_task_logger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def sync_sentinel2_vegetation(self, zone_ids=None):
    """
    Sync vegetation indices (NDVI, NDWI, NBR, NDMI) from Sentinel-2.
    """
    try:
        from data_providers.sentinel2 import Sentinel2Provider
        from apps.geography.models import MonitoringZone
        from django.utils import timezone
        from datetime import timedelta
        from django.conf import settings

        provider = Sentinel2Provider(
            client_id=getattr(settings, "CDSE_CLIENT_ID", ""),
            client_secret=getattr(settings, "CDSE_CLIENT_SECRET", ""),
        )

        # Get zones (no is_active field — all zones are active)
        if zone_ids:
            zones = MonitoringZone.objects.filter(id__in=zone_ids)
        else:
            zones = MonitoringZone.objects.all()

        if not zones.exists():
            logger.info("No zones found for Sentinel-2 sync")
            return {"synced_zones": 0, "status": "no_zones"}

        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=30)

        total_saved = 0
        zones_synced = 0

        for zone in zones:
            try:
                aoi = {
                    "west": zone.longitude - 0.5 if zone.longitude else -12.0,
                    "south": zone.latitude - 0.5 if zone.latitude else 10.0,
                    "east": zone.longitude + 0.5 if zone.longitude else 4.0,
                    "north": zone.latitude + 0.5 if zone.latitude else 25.0,
                }

                # Fetch bands for all indices
                fetched = provider.fetch(
                    aoi=aoi,
                    start_date=start_date.isoformat(),
                    end_date=end_date.isoformat(),
                    bands=["B03", "B04", "B08", "B11", "B12"],
                    max_cloud_cover=30,
                )

                if fetched:
                    # Normalize each result
                    all_normalized = []
                    for result in fetched:
                        normalized = provider.normalize(result)
                        all_normalized.extend(normalized)

                    # Save
                    saved_count = provider.save(all_normalized)
                    total_saved += saved_count

                    if saved_count > 0:
                        zones_synced += 1
                        logger.info("Synced %d vegetation observations for zone %s", saved_count, zone.name)

            except Exception as e:
                logger.warning("Failed to sync Sentinel-2 for zone %s: %s", zone.name, e)
                continue

        result = {
            "synced_zones": zones_synced,
            "total_observations": total_saved,
            "date_range": f"{start_date} to {end_date}",
            "status": "success",
        }
        logger.info("Sentinel-2 sync completed: %s", result)
        return result

    except Exception as exc:
        logger.error("Sentinel-2 sync failed: %s", exc)
        self.retry(exc=exc)


@shared_task
def sync_sentinel2_for_zone(zone_id):
    """Sync Sentinel-2 data for a single zone."""
    return sync_sentinel2_vegetation.delay(zone_ids=[zone_id])
