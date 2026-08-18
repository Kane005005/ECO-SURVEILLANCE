from typing import Dict, Any
from decimal import Decimal
from django.utils import timezone
from apps.sensors.models import MonitoringStation, Sensor, SensorReading, SensorType
import random

class SensorSimulator:
    SCENARIO_NORMAL = "NORMAL"
    SCENARIO_WATER_POLLUTION = "WATER_POLLUTION"
    SCENARIO_DROUGHT = "DROUGHT"
    SCENARIO_HEAT = "HEAT"
    SCENARIO_ATMOSPHERIC_ANOMALY = "ATMOSPHERIC_ANOMALY"
    SCENARIO_SENSOR_OFFLINE = "SENSOR_OFFLINE"

    SCENARIOS = [SCENARIO_NORMAL, SCENARIO_WATER_POLLUTION, SCENARIO_DROUGHT, SCENARIO_HEAT, SCENARIO_ATMOSPHERIC_ANOMALY, SCENARIO_SENSOR_OFFLINE]

    READING_VALUES = {
        SCENARIO_NORMAL: {
            SensorType.TEMPERATURE: (26.0, 30.0, "°C"),
            SensorType.PH: (6.5, 7.5, ""),
            SensorType.TURBIDITY: (15.0, 30.0, "NTU"),
            SensorType.CONDUCTIVITY: (300.0, 450.0, "µS/cm"),
            SensorType.DISSOLVED_OXYGEN: (5.0, 7.0, "mg/L"),
            SensorType.WATER_LEVEL: (2.5, 3.5, "m"),
        },
        SCENARIO_WATER_POLLUTION: {
            SensorType.TEMPERATURE: (26.0, 29.0, "°C"),
            SensorType.PH: (4.5, 5.8, ""),
            SensorType.TURBIDITY: (150.0, 220.0, "NTU"),
            SensorType.CONDUCTIVITY: (1000.0, 1500.0, "µS/cm"),
            SensorType.DISSOLVED_OXYGEN: (1.5, 2.5, "mg/L"),
            SensorType.WATER_LEVEL: (2.0, 3.0, "m"),
        },
        SCENARIO_DROUGHT: {
            SensorType.TEMPERATURE: (37.0, 42.0, "°C"),
            SensorType.PH: (7.2, 8.0, ""),
            SensorType.TURBIDITY: (70.0, 110.0, "NTU"),
            SensorType.CONDUCTIVITY: (850.0, 1100.0, "µS/cm"),
            SensorType.DISSOLVED_OXYGEN: (2.8, 4.0, "mg/L"),
            SensorType.WATER_LEVEL: (0.2, 0.6, "m"),
        },
        SCENARIO_HEAT: {
            SensorType.TEMPERATURE: (42.0, 46.0, "°C"),
            SensorType.PH: (6.8, 7.4, ""),
            SensorType.TURBIDITY: (30.0, 45.0, "NTU"),
            SensorType.CONDUCTIVITY: (380.0, 450.0, "µS/cm"),
            SensorType.DISSOLVED_OXYGEN: (4.0, 5.0, "mg/L"),
            SensorType.WATER_LEVEL: (2.5, 3.2, "m"),
        },
        SCENARIO_ATMOSPHERIC_ANOMALY: {
            SensorType.TEMPERATURE: (28.0, 32.0, "°C"),
            SensorType.PH: (6.5, 7.0, ""),
            SensorType.TURBIDITY: (20.0, 35.0, "NTU"),
            SensorType.CONDUCTIVITY: (320.0, 400.0, "µS/cm"),
            SensorType.DISSOLVED_OXYGEN: (5.0, 6.0, "mg/L"),
            SensorType.NO2: (40.0, 65.0, "µg/m³"),
            SensorType.PM25: (50.0, 80.0, "µg/m³"),
        },
    }

    def generate_readings(self, station: MonitoringStation, scenario: str = SCENARIO_NORMAL) -> list:
        if scenario == self.SCENARIO_SENSOR_OFFLINE:
            return []

        readings_data = self.READING_VALUES.get(scenario, self.READING_VALUES[self.SCENARIO_NORMAL])
        now = timezone.now()
        readings = []

        sensors = Sensor.objects.filter(station=station, is_active=True)
        for sensor in sensors:
            if sensor.sensor_type in readings_data:
                low, high, unit = readings_data[sensor.sensor_type]
                value = round(random.uniform(low, high), 2)
                readings.append(SensorReading(
                    sensor=sensor,
                    value=value,
                    recorded_at=now,
                    is_simulated=True,
                ))

        if readings:
            SensorReading.objects.bulk_create(readings)
        return readings

    def simulate_all_stations(self, scenario: str = SCENARIO_NORMAL):
        stations = MonitoringStation.objects.filter(status="ACTIVE")
        total = 0
        for station in stations:
            readings = self.generate_readings(station, scenario)
            total += len(readings)
        return total
