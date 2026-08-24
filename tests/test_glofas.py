from django.test import TestCase
from datetime import date
from apps.water.models import HydrologicalStation, RiverForecast
from apps.geography.models import MonitoringZone
from data_providers.glofas import GloFASProvider


class GloFASProviderTest(TestCase):
    """Tests unitaires pour le provider hydrologique Copernicus GloFAS."""

    def setUp(self):
        self.zone = MonitoringZone.objects.create(
            name="Zone Mopti", zone_type="WETLAND", latitude=14.4958, longitude=-4.1856, area_km2=500
        )
        self.station = HydrologicalStation.objects.create(
            nom="Mopti",
            cours_d_eau="Niger",
            latitude=14.4958,
            longitude=-4.1856,
            seuil_vigilance=1600.0,
            seuil_alerte=2800.0,
            seuil_danger=4000.0,
            zone=self.zone,
            is_active=True,
        )
        self.provider = GloFASProvider(cds_key="", demo_mode=True)

    def test_health_check_demo_mode(self):
        health = self.provider.health_check()
        self.assertEqual(health.status, "ok")
        self.assertIn("démo", health.reason.lower())

    def test_search_dataset_query(self):
        query = self.provider.search(date="2026-08-24")
        self.assertEqual(len(query), 1)
        self.assertEqual(query[0]["dataset"], "cems-glofas-forecast")
        self.assertEqual(query[0]["variable"], "river_discharge_in_the_last_24_hours")
        self.assertEqual(query[0]["area"], [25.0, -12.5, 10.0, 4.5])

    def test_fetch_and_river_snapping_simulation(self):
        results = self.provider.fetch(date="2026-08-24")
        self.assertGreaterEqual(len(results), 3)
        for res in results:
            data = res.data
            self.assertEqual(data["station_id"], self.station.id)
            self.assertIn(data["leadtime_hours"], [24, 48, 72])
            self.assertGreater(data["discharge_m3s"], 0)
            self.assertIn(data["alert_level"], ["GREEN", "YELLOW", "ORANGE", "RED"])

    def test_save_forecasts_persists_in_database(self):
        results = self.provider.fetch(date="2026-08-24")
        normalized = self.provider.normalize(results)
        saved = self.provider.save(normalized)
        self.assertEqual(saved, len(normalized))
        self.assertEqual(RiverForecast.objects.filter(station=self.station).count(), len(normalized))

    def test_alert_level_thresholds(self):
        # Green
        self.assertEqual(self.provider._compute_alert_level(1200.0, 5.0, self.station), "GREEN")
        # Yellow
        self.assertEqual(self.provider._compute_alert_level(1700.0, 10.0, self.station), "YELLOW")
        # Orange
        self.assertEqual(self.provider._compute_alert_level(2900.0, 10.0, self.station), "ORANGE")
        # Red
        self.assertEqual(self.provider._compute_alert_level(4200.0, 35.0, self.station), "RED")
