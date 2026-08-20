from celery import shared_task
import logging

logger = logging.getLogger("apps.anomalies")


@shared_task(bind=True, ignore_result=True)
def run_anomaly_detection(self):
    """Run anomaly detection across all zones using multi-source analysis."""
    from apps.geography.models import MonitoringZone
    from apps.anomalies.models import Anomaly
    from core.services.anomaly import ZoneAnomalyScanner
    from django.utils import timezone

    scanner = ZoneAnomalyScanner()
    zones = MonitoringZone.objects.all()
    total = 0

    for zone in zones:
        try:
            anomalies = scanner.scan_zone(zone)
            for anom_data in anomalies:
                # Dedup: don't create same anomaly type + zone in last 24h
                if Anomaly.objects.filter(
                    zone=zone, anomaly_type=anom_data["anomaly_type"],
                    detected_at__gte=timezone.now() - __import__("datetime").timedelta(hours=24)
                ).exists():
                    continue

                Anomaly.objects.create(
                    anomaly_type=anom_data["anomaly_type"],
                    zone=zone,
                    source=anom_data.get("source", "AnomalyEngine"),
                    detected_at=timezone.now(),
                    severity=anom_data["severity"],
                    score=min(abs(anom_data.get("z_score", 0)) * 15, 100) if "z_score" in anom_data else 50,
                    confidence=min(abs(anom_data.get("z_score", 0)) / 4.0, 1.0) if "z_score" in anom_data else 0.5,
                    metric=anom_data.get("metric", ""),
                    current_value=anom_data.get("current_value"),
                    baseline_value=anom_data.get("baseline_value"),
                    z_score=anom_data.get("z_score"),
                    description=anom_data.get("description", ""),
                    status="NEW",
                    is_simulated=anom_data.get("is_simulated", False),
                )
                total += 1
        except Exception as e:
            logger.warning("Anomaly scan failed for zone %s: %s", zone.name, str(e))

    logger.info("Anomaly detection complete: %d anomalies found across %d zones", total, zones.count())
    return {"status": "ok", "anomalies": total, "zones": zones.count()}
