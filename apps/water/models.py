from django.db import models

class WaterBody(models.Model):
    BODY_TYPES = [
        ("RIVER", "Rivière"),
        ("LAKE", "Lac"),
        ("RESERVOIR", "Réservoir"),
        ("POND", "Mare"),
        ("DAM", "Barrage"),
    ]
    name = models.CharField(max_length=255)
    body_type = models.CharField(max_length=32, choices=BODY_TYPES)
    zone = models.ForeignKey("geography.MonitoringZone", on_delete=models.SET_NULL, null=True, blank=True, related_name="water_bodies")
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    area_km2 = models.FloatField(null=True, blank=True)
    is_simulated = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.get_body_type_display()})"

class WaterObservation(models.Model):
    METRIC_CHOICES = [
        ("TEMPERATURE", "Température"),
        ("PH", "pH"),
        ("TURBIDITY", "Turbidité"),
        ("CONDUCTIVITY", "Conductivité"),
        ("DISSOLVED_OXYGEN", "Oxygène dissous"),
        ("WATER_LEVEL", "Niveau d'eau"),
    ]
    water_body = models.ForeignKey(WaterBody, on_delete=models.CASCADE, related_name="observations")
    metric = models.CharField(max_length=32, choices=METRIC_CHOICES)
    value = models.FloatField()
    unit = models.CharField(max_length=32, blank=True)
    baseline_value = models.FloatField(null=True, blank=True)
    std_dev = models.FloatField(null=True, blank=True)
    measured_at = models.DateTimeField()
    source = models.CharField(max_length=128, default="Sensor")
    is_simulated = models.BooleanField(default=False)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-measured_at"]
        indexes = [
            models.Index(fields=["water_body", "metric", "-measured_at"]),
        ]

    def __str__(self):
        return f"{self.metric}={self.value} in {self.water_body.name}"
