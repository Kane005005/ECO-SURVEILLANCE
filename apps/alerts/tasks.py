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
def sync_firms_and_evaluate_alerts(self):
    """Sync FIRMS data then re-evaluate alerts."""
    from apps.fires.tasks import sync_firms_data
    sync_firms_data()
    evaluate_all_alerts.delay()
    return {"status": "ok"}
