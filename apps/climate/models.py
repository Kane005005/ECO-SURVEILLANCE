from django.db import models

class ClimateObservation(models.Model):
    VARIABLE_CHOICES = [
        ("TEMPERATURE", "Température"),
        ("PRECIPITATION", "Précipitations"),
        ("HUMIDITY", "Humidité"),
        ("WIND_SPEED", "Vitesse du vent"),
        ("WIND_DIRECTION", "Direction du vent"),
        ("PRESSURE", "Pression"),
        ("RADIATION", "Rayonnement solaire"),
    ]
    zone = models.ForeignKey("geography.MonitoringZone", on_delete=models.CASCADE, related_name="climate_observations")
    variable = models.CharField(max_length=32, choices=VARIABLE_CHOICES)
    value = models.FloatField()
    unit = models.CharField(max_length=32, blank=True)
    baseline_value = models.FloatField(null=True, blank=True)
    std_dev = models.FloatField(null=True, blank=True)
    observed_at = models.DateTimeField()
    source = models.CharField(max_length=128, default="NASA POWER")
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
