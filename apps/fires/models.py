from django.db import models

class FireDetection(models.Model):
    latitude = models.FloatField()
    longitude = models.FloatField()
    detected_at = models.DateTimeField()
    satellite = models.CharField(max_length=64, blank=True, default="MODIS")
    confidence = models.CharField(max_length=20, blank=True, default="nominal")
    brightness = models.FloatField(null=True, blank=True)
    frp = models.FloatField(null=True, blank=True, help_text="Fire Radiative Power")
    scan = models.FloatField(null=True, blank=True)
    track = models.FloatField(null=True, blank=True)
    bright_t31 = models.FloatField(null=True, blank=True)
    daynight = models.CharField(max_length=10, blank=True, default="D")
    source = models.CharField(max_length=128, blank=True, default="NASA FIRMS")
    is_simulated = models.BooleanField(default=False)
    zone = models.ForeignKey("geography.MonitoringZone", on_delete=models.SET_NULL, null=True, blank=True, related_name="fires")
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-detected_at"]
        indexes = [
            models.Index(fields=["-detected_at"]),
            models.Index(fields=["latitude", "longitude"]),
        ]

    def __str__(self):
        return f"Fire at ({self.latitude}, {self.longitude}) - {self.detected_at}"
