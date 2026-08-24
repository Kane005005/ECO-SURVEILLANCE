from django.test import TestCase
from django.utils import timezone
from datetime import timedelta, date
from apps.geography.models import MonitoringZone
from apps.water.models import HydrologicalStation, RiverForecast, FloodObservation
from apps.fires.models import FireDetection
from apps.climate.models import ClimateObservation
from apps.vegetation.models import VegetationObservation
from apps.atmosphere.models import AtmosphericObservation
from apps.incidents.models import Incident
from apps.satellite.models import SatelliteObservation
from core.services.eco_engine import ECOEngine


class ECOEngineTest(TestCase):
    """Tests unitaires pour le moteur central ECO Engine et les corrélations croisées."""

    def setUp(self):
        self.zone = MonitoringZone.objects.create(
            name="Zone Mopti Delta",
            zone_type="WETLAND",
            latitude=14.5,
            longitude=-4.2,
            area_km2=1500,
        )
        self.station = HydrologicalStation.objects.create(
            nom="Mopti Port",
            cours_d_eau="Niger",
            latitude=14.5,
            longitude=-4.2,
            seuil_vigilance=1600.0,
            seuil_alerte=2800.0,
            seuil_danger=4000.0,
            zone=self.zone,
            is_active=True,
        )
        self.engine = ECOEngine()

    def test_rule1_flood_confirmation(self):
        # 1. High GloFAS discharge
        RiverForecast.objects.create(
            station=self.station,
            date_run=timezone.now().date(),
            leadtime_hours=24,
            discharge_m3s=3100.0,
            trend_72h_pct=35.0,
            alert_level="ORANGE",
        )
        # 2. Observed flood by LANCE > 5 km2
        FloodObservation.objects.create(
            zone=self.zone,
            tile_name="h17v07",
            observation_date=timezone.now().date(),
            flooded_area_km2=45.0,
            flooded_pixels_count=850,
            source="NASA LANCE VIIRS NRT3",
        )

        alerts = self.engine.evaluate_zone_correlations(self.zone)
        self.assertGreater(len(alerts), 0)

        flood_alert = next((a for a in alerts if a["rule_name"] == "CRUE_CONFIRMEE_GLOFAS_LANCE"), None)
        self.assertIsNotNone(flood_alert)
        self.assertEqual(flood_alert["severity"], "CRITICAL")
        self.assertIn("GloFAS", flood_alert["sources"])

        # Check that Sentinel-2 NDWI triggered task was created
        s2_obs = SatelliteObservation.objects.filter(zone=self.zone, satellite="SENTINEL2").first()
        self.assertIsNotNone(s2_obs)
        self.assertIn("NDWI", s2_obs.source)

    def test_rule2_fire_extreme_weather(self):
        now = timezone.now()
        FireDetection.objects.create(
            zone=self.zone,
            latitude=14.5,
            longitude=-4.2,
            detected_at=now,
            confidence="high",
            brightness=340.0,
            frp=45.0,
        )
        ClimateObservation.objects.create(
            zone=self.zone, variable="TEMPERATURE", value=41.5, observed_at=now
        )
        ClimateObservation.objects.create(
            zone=self.zone, variable="HUMIDITY", value=15.0, observed_at=now
        )
        ClimateObservation.objects.create(
            zone=self.zone, variable="WIND_SPEED", value=7.5, observed_at=now
        )

        alerts = self.engine.evaluate_zone_correlations(self.zone)
        fire_alert = next((a for a in alerts if a["rule_name"] == "INCENDIE_METEO_EXTREME"), None)
        self.assertIsNotNone(fire_alert)
        self.assertIn(fire_alert["severity"], ["HIGH", "CRITICAL"])

    def test_rule3_agro_drought(self):
        now = timezone.now()
        # Very low precipitation
        ClimateObservation.objects.create(
            zone=self.zone, variable="PRECIPITATION", value=5.0, observed_at=now - timedelta(days=5)
        )
        # Low NDVI
        VegetationObservation.objects.create(
            zone=self.zone, index_name="NDVI", value=0.22, acquisition_date=now.date()
        )

        alerts = self.engine.evaluate_zone_correlations(self.zone)
        drought_alert = next((a for a in alerts if a["rule_name"] == "SECHERESSE_AGRO_CLIMATIQUE"), None)
        self.assertIsNotNone(drought_alert)
        self.assertEqual(drought_alert["severity"], "HIGH")

    def test_rule4_harmattan_air_quality(self):
        now = timezone.now()
        AtmosphericObservation.objects.create(
            zone=self.zone, variable="PM25", value=85.0, observed_at=now
        )
        AtmosphericObservation.objects.create(
            zone=self.zone, variable="AEROSOL", value=1.8, observed_at=now
        )
        ClimateObservation.objects.create(
            zone=self.zone, variable="WIND_SPEED", value=5.5, observed_at=now
        )

        alerts = self.engine.evaluate_zone_correlations(self.zone)
        air_alert = next((a for a in alerts if a["rule_name"] == "POUSSIERE_HARMATTAN_AIR"), None)
        self.assertIsNotNone(air_alert)
        self.assertIn(air_alert["severity"], ["MEDIUM", "HIGH"])

    def test_run_all_correlations(self):
        results = self.engine.run_all_correlations()
        self.assertIsInstance(results, list)
