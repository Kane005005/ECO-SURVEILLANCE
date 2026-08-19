"""
Celery tasks for Sentinel-5P atmospheric data sync.
"""
from celery import shared_task
from celery.utils.log import get_task_logger

logger = get_task_logger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def sync_sentinel5p_atmospheric(self, zone_ids=None, variables=None):
    """
    Sync atmospheric data (SO2, O3, NO2, AER_AI) from Sentinel-5P.
    """
    try:
        from data_providers.sentinel5p import Sentinel5PProvider
        from apps.geography.models import MonitoringZone
        from django.utils import timezone
        from datetime import timedelta
        from django.conf import settings

        provider = Sentinel5PProvider(
            client_id=getattr(settings, "CDSE_CLIENT_ID", ""),
            client_secret=getattr(settings, "CDSE_CLIENT_SECRET", ""),
        )

        if variables is None:
            variables = ["SO2", "O3", "NO2", "AER_AI"]

        # Get zones (no is_active field)
        if zone_ids:
            zones = MonitoringZone.objects.filter(id__in=zone_ids)
        else:
            zones = MonitoringZone.objects.all()

        if not zones.exists():
            logger.info("No zones found for Sentinel-5P sync")
            return {"synced_zones": 0, "status": "no_zones"}

        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=5)

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

                zone_saved = 0
                for variable in variables:
                    fetched = provider.fetch(
                        product_key=variable,
                        aoi=aoi,
                        start_date=start_date.isoformat(),
                        end_date=end_date.isoformat(),
                    )

                    if fetched:
                        all_normalized = []
                        for result in fetched:
                            normalized = provider.normalize(result)
                            all_normalized.extend(normalized)

                        saved_count = provider.save(all_normalized)
                        zone_saved += saved_count

                total_saved += zone_saved
                if zone_saved > 0:
                    zones_synced += 1
                    logger.info("Synced %d atmospheric observations for zone %s", zone_saved, zone.name)

            except Exception as e:
                logger.warning("Failed to sync Sentinel-5P for zone %s: %s", zone.name, e)
                continue

        result = {
            "synced_zones": zones_synced,
            "total_observations": total_saved,
            "variables_synced": variables,
            "date_range": f"{start_date} to {end_date}",
            "status": "success",
        }
        logger.info("Sentinel-5P sync completed: %s", result)
        return result

    except Exception as exc:
        logger.error("Sentinel-5P sync failed: %s", exc)
        self.retry(exc=exc)


@shared_task
def sync_sentinel5p_for_zone(zone_id, variables=None):
    """Sync Sentinel-5P data for a single zone."""
    return sync_sentinel5p_atmospheric.delay(zone_ids=[zone_id], variables=variables)
