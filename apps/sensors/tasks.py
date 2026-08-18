from celery import shared_task
import logging

logger = logging.getLogger("apps.sensors")

@shared_task(bind=True, ignore_result=True)
def simulate_all_stations(self):
    from .services import SensorSimulator
    simulator = SensorSimulator()
    total = simulator.simulate_all_stations(SensorSimulator.SCENARIO_NORMAL)
    logger.info("Simulated %d readings across all stations", total)
    return {"status": "ok", "readings": total}
