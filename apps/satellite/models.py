from django.db import models

class SatelliteObservation(models.Model):
    SATELLITE_CHOICES = [
        ("SENTINEL2", "Sentinel-2"),
        ("SENTINEL1", "Sentinel-1"),
        ("SENTINEL5P", "Sentinel-5P"),
        ("LANDSAT8", "Landsat 8"),
        ("LANDSAT9", "Landsat 9"),
    ]
    PRODUCT_CHOICES = [
        ("L2A", "Level-2A"),
        ("L1C", "Level-1C"),
        ("TOA", "Top of Atmosphere"),
    ]

    zone = models.ForeignKey("geography.MonitoringZone", on_delete=models.CASCADE, related_name="satellite_observations")
    satellite = models.CharField(max_length=32, choices=SATELLITE_CHOICES)
    product_type = models.CharField(max_length=16, choices=PRODUCT_CHOICES, blank=True)
    acquisition_time = models.DateTimeField()
    cloud_cover = models.FloatField(default=0.0)
    source = models.CharField(max_length=128, default="Copernicus")
    is_simulated = models.BooleanField(default=False)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-acquisition_time"]

    def __str__(self):
        return f"{self.satellite} - {self.zone.name} ({self.acquisition_time})"
