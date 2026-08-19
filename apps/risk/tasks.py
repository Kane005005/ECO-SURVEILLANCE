from celery import shared_task
import logging

logger = logging.getLogger("apps.risk")


@shared_task(bind=True, ignore_result=True)
def compute_all_risks(self):
    """Compute risk assessments for all zones."""
    from apps.geography.models import MonitoringZone
    from apps.risk.models import RiskAssessment
    from core.services.risk import RiskEngine
    from django.utils import timezone

    engine = RiskEngine()
    zones = MonitoringZone.objects.all()
    count = 0

    for zone in zones:
        try:
            results = engine.compute_all_risks(zone)
            for result in results:
                if RiskAssessment.objects.filter(
                    zone=zone, risk_type=result.risk_type,
                    calculated_at__date=timezone.now().date()
                ).exists():
                    continue

                RiskAssessment.objects.create(
                    zone=zone,
                    risk_type=result.risk_type,
                    risk_score=result.risk_score,
                    confidence_score=result.confidence * 100,
                    level=result.level,
                    severity=result.severity,
                    factors=[
                        {"name": f.name, "score": f.score, "weight": f.weight, "description": f.description}
                        for f in result.factors
                    ],
                    algorithm_version=result.algorithm_version,
                    calculated_at=timezone.now(),
                    is_simulated=False,
                )
                count += 1
        except Exception as e:
            logger.warning("Risk computation failed for zone %s: %s", zone.name, str(e))

    logger.info("Risk computation complete: %d assessments for %d zones", count, zones.count())
    return {"status": "ok", "assessments": count, "zones": zones.count()}
