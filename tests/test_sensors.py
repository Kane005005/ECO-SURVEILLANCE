from django.test import TestCase
from apps.sensors.models import MonitoringStation, Sensor, SensorReading, SensorType
from apps.sensors.services import SensorSimulator
from apps.geography.models import MonitoringZone


class SensorSimulationTest(TestCase):
    """Tests for the sensor simulation system."""

    def setUp(self):
        self.zone = MonitoringZone.objects.create(
            name="Zone Test", zone_type="WATER", latitude=12.64, longitude=-8.0, area_km2=100
        )
        self.station = MonitoringStation.objects.create(
            code="ST01", name="Station Test", zone=self.zone, status="ACTIVE",
            latitude=12.64, longitude=-8.0
        )
        self.sensor_temp = Sensor.objects.create(
            station=self.station, sensor_type=SensorType.TEMPERATURE, code="T01", is_active=True
        )
        self.sensor_ph = Sensor.objects.create(
            station=self.station, sensor_type=SensorType.PH, code="PH01", is_active=True
        )
        self.simulator = SensorSimulator()

    def test_simulate_normal(self):
        readings = self.simulator.generate_readings(self.station, SensorSimulator.SCENARIO_NORMAL)
        self.assertGreater(len(readings), 0)
        for r in readings:
            self.assertTrue(r.is_simulated)
            self.assertIsNotNone(r.value)
            self.assertIsNotNone(r.recorded_at)

    def test_simulate_drought(self):
        readings = self.simulator.generate_readings(self.station, SensorSimulator.SCENARIO_DROUGHT)
        self.assertGreater(len(readings), 0)
        temp_readings = [r for r in readings if r.sensor.sensor_type == SensorType.TEMPERATURE]
        if temp_readings:
            self.assertGreater(temp_readings[0].value, 35)

    def test_simulate_offline_returns_empty(self):
        readings = self.simulator.generate_readings(self.station, SensorSimulator.SCENARIO_SENSOR_OFFLINE)
        self.assertEqual(len(readings), 0)

    def test_simulate_all_stations(self):
        total = self.simulator.simulate_all_stations(SensorSimulator.SCENARIO_NORMAL)
        self.assertGreater(total, 0)
        self.assertEqual(SensorReading.objects.count(), total)

    def test_scenarios_list(self):
        self.assertIn(SensorSimulator.SCENARIO_NORMAL, SensorSimulator.SCENARIOS)
        self.assertIn(SensorSimulator.SCENARIO_DROUGHT, SensorSimulator.SCENARIOS)
        self.assertIn(SensorSimulator.SCENARIO_WATER_POLLUTION, SensorSimulator.SCENARIOS)
