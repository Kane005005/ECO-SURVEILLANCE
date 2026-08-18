from django.db import models

class MonitoringStation(models.Model):
    STATUS_CHOICES = [
        ("ACTIVE", "Active"),
        ("DEGRADED", "Dégradée"),
        ("OFFLINE", "Hors ligne"),
    ]
    code = models.CharField(max_length=64, unique=True)
    name = models.CharField(max_length=255)
    zone = models.ForeignKey("geography.MonitoringZone", on_delete=models.SET_NULL, null=True, blank=True, related_name="stations")
    latitude = models.FloatField()
    longitude = models.FloatField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="ACTIVE")
    is_simulated = models.BooleanField(default=True)
    battery_level = models.IntegerField(default=100)
    installed_at = models.DateTimeField(null=True, blank=True)
    last_seen_at = models.DateTimeField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["code"]

    def __str__(self):
        return f"{self.code} - {self.name}"

class SensorType(models.TextChoices):
    TEMPERATURE = "TEMPERATURE", "Température"
    PH = "PH", "pH"
    TURBIDITY = "TURBIDITY", "Turbidité"
    CONDUCTIVITY = "CONDUCTIVITY", "Conductivité"
    DISSOLVED_OXYGEN = "DISSOLVED_OXYGEN", "Oxygène dissous"
    WATER_LEVEL = "WATER_LEVEL", "Niveau d'eau"
    NO2 = "NO2", "NO₂"
    PM25 = "PM25", "PM2.5"
    PM10 = "PM10", "PM10"

class Sensor(models.Model):
    station = models.ForeignKey(MonitoringStation, on_delete=models.CASCADE, related_name="sensors")
    sensor_type = models.CharField(max_length=32, choices=SensorType.choices)
    code = models.CharField(max_length=128)
    unit = models.CharField(max_length=64, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("station", "sensor_type", "code")

    def __str__(self):
        return f"{self.station.code}/{self.sensor_type}"

class SensorReading(models.Model):
    sensor = models.ForeignKey(Sensor, on_delete=models.CASCADE, related_name="readings")
    value = models.FloatField()
    recorded_at = models.DateTimeField()
    quality = models.CharField(max_length=32, default="GOOD")
    is_simulated = models.BooleanField(default=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-recorded_at"]
        indexes = [
            models.Index(fields=["sensor", "-recorded_at"]),
        ]

    def __str__(self):
        return f"{self.sensor}: {self.value} at {self.recorded_at}"
