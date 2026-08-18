from celery import shared_task
import logging

logger = logging.getLogger("apps.anomalies")

@shared_task(bind=True, ignore_result=True)
def run_anomaly_detection(self):
    from apps.geography.models import MonitoringZone
    from apps.anomalies.services import AnomalyDetectionService
    from apps.vegetation.models import VegetationObservation
    from apps.water.models import WaterObservation
    from apps.climate.models import ClimateObservation

    service = AnomalyDetectionService()
    zones = MonitoringZone.objects.all()
    total = 0

    for zone in zones:
        veg_obs = VegetationObservation.objects.filter(zone=zone).order_by("-acquisition_date")[:1]
        total += len(service.detect_from_observations(zone, list(veg_obs), "VEGETATION", "AnomalyEngine"))

        water_obs = WaterObservation.objects.filter(zone=zone).order_by("-measured_at")[:1]
        total += len(service.detect_from_observations(zone, list(water_obs), "WATER", "AnomalyEngine"))

        climate_obs = ClimateObservation.objects.filter(zone=zone).order_by("-observed_at")[:1]
        total += len(service.detect_from_observations(zone, list(climate_obs), "CLIMATE", "AnomalyEngine"))

    logger.info("Anomaly detection complete: %d anomalies found", total)
    return {"status": "ok", "anomalies": total}
