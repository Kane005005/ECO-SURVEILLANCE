from celery import shared_task
import logging

logger = logging.getLogger("apps.alerts")


@shared_task(bind=True, ignore_result=True)
def evaluate_all_alerts(self):
    """Evaluate alert rules for all zones and create alerts."""
    from core.services.alert_engine import AlertEngine

    engine = AlertEngine()
    alerts = engine.evaluate_all_zones()
    logger.info("Alert evaluation complete: %d alerts created", len(alerts))
    return {"status": "ok", "alerts_created": len(alerts)}


@shared_task(bind=True, ignore_result=True)
def run_eco_engine(self):
    """Run central multi-source ECO Engine cross-correlations."""
    from core.services.eco_engine import ECOEngine

    engine = ECOEngine()
    alerts = engine.run_all_correlations()
    logger.info("ECO Engine run complete: %d correlated alerts evaluated.", len(alerts))
    return {"status": "ok", "correlated_alerts": len(alerts)}

