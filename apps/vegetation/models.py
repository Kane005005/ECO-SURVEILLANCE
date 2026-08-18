from django.db import models

class VegetationObservation(models.Model):
    INDEX_CHOICES = [
        ("NDVI", "NDVI"),
        ("NDWI", "NDWI"),
        ("EVI", "EVI"),
        ("SAVI", "SAVI"),
    ]
    zone = models.ForeignKey("geography.MonitoringZone", on_delete=models.CASCADE, related_name="vegetation_observations")
    index_name = models.CharField(max_length=16, choices=INDEX_CHOICES, default="NDVI")
    value = models.FloatField()
    baseline_value = models.FloatField(null=True, blank=True)
    std_dev = models.FloatField(null=True, blank=True)
    acquisition_date = models.DateField()
    source = models.CharField(max_length=128, default="Sentinel-2")
    is_simulated = models.BooleanField(default=False)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-acquisition_date"]
        indexes = [
            models.Index(fields=["zone", "index_name", "-acquisition_date"]),
        ]

    def __str__(self):
        return f"{self.index_name}={self.value:.3f} in {self.zone.name} on {self.acquisition_date}"
