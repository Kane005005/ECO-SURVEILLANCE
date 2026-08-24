"""
Celery application configuration for ECO-SURVEILLANCE MALI.
"""
from celery import Celery
from celery.schedules import crontab
import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

app = Celery("eco_surveillance")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()

# Beat schedule — configurable periodicity
app.conf.beat_schedule = {
    # Copernicus GloFAS hydrology sync — daily at 01:00 UTC
    "sync-glofas-hydrology": {
        "task": "apps.water.tasks.sync_glofas_hydrology",
        "schedule": crontab(hour=1, minute=0),
    },
    # NASA LANCE Flood VIIRS NRT3 sync — daily at 04:00 UTC
    "sync-lance-flood": {
        "task": "apps.water.tasks.sync_lance_flood",
        "schedule": crontab(hour=4, minute=0),
    },
    # NASA FIRMS fire detection sync — every 3 hours
    "sync-firms-fires": {
        "task": "apps.fires.tasks.sync_firms_data",
        "schedule": crontab(hour="*/3", minute=0),
    },
    # NASA POWER climate data — daily at 05:00 UTC
    "sync-nasa-power-climate": {
        "task": "apps.climate.tasks.sync_nasa_power",
        "schedule": crontab(hour=5, minute=0),
    },
    # ECO Engine Multi-Source Cross-Correlations — every 6 hours
    "run-eco-engine": {
        "task": "apps.alerts.tasks.run_eco_engine",
        "schedule": crontab(hour="*/6", minute=0),
    },
    # Sensor simulation — every hour
    "simulate-sensors": {
        "task": "apps.sensors.tasks.simulate_all_stations",
        "schedule": crontab(minute=0),
    },
    # Anomaly detection — every 12 hours
    "detect-anomalies": {
        "task": "apps.anomalies.tasks.run_anomaly_detection",
        "schedule": crontab(hour="*/12", minute=30),
    },
    # IEZ computation — daily at 08:00 UTC
    "compute-iez": {
        "task": "apps.iez.tasks.compute_all_iez",
        "schedule": crontab(hour=8, minute=0),
    },
    # Sentinel-2 vegetation sync — daily at 02:00 UTC
    "sync-sentinel2-vegetation": {
        "task": "apps.vegetation.tasks.sync_sentinel2_vegetation",
        "schedule": crontab(hour=2, minute=0),
    },
    # Sentinel-5P atmospheric sync — every 2 days at 04:30 UTC
    "sync-sentinel5p-atmospheric": {
        "task": "apps.atmosphere.tasks.sync_sentinel5p_atmospheric",
        "schedule": crontab(hour="*/2", minute=30),
    },
    # Risk computation — daily at 09:00 UTC (after anomalies + IEZ)
    "compute-all-risks": {
        "task": "apps.risk.tasks.compute_all_risks",
        "schedule": crontab(hour=9, minute=0),
    },
}
