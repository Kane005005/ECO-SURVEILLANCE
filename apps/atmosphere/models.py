from django.db import models

class AtmosphericObservation(models.Model):
    VARIABLE_CHOICES = [
        ("NO2", "NO₂"),
        ("SO2", "SO₂"),
        ("CO", "CO"),
        ("CH4", "CH₄"),
        ("O3", "O₃"),
        ("AEROSOLS", "Aérosols"),
        ("PM25", "PM2.5"),
        ("PM10", "PM10"),
    ]
    zone = models.ForeignKey("geography.MonitoringZone", on_delete=models.CASCADE, related_name="atmospheric_observations")
    variable = models.CharField(max_length=32, choices=VARIABLE_CHOICES)
    value = models.FloatField()
    unit = models.CharField(max_length=32, blank=True)
    baseline_value = models.FloatField(null=True, blank=True)
    std_dev = models.FloatField(null=True, blank=True)
    observed_at = models.DateTimeField()
    source = models.CharField(max_length=128, default="Sentinel-5P")
    quality_flag = models.CharField(max_length=32, blank=True, default="GOOD")
    is_simulated = models.BooleanField(default=False)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-observed_at"]
        indexes = [
            models.Index(fields=["zone", "variable", "-observed_at"]),
        ]

    def __str__(self):
        return f"{self.variable}={self.value} in {self.zone.name}"
