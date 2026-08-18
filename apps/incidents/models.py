from django.db import models

class Incident(models.Model):
    TYPE_CHOICES = [
        ("WILDFIRE", "Feu de forêt"),
        ("DROUGHT", "Sécheresse"),
        ("VEGETATION_DEGRADATION", "Dégradation végétale"),
        ("WATER_POLLUTION", "Pollution eau"),
        ("WATER_STRESS", "Stress hydrique"),
        ("ATMOSPHERIC_ANOMALY", "Anomalie atmosphérique"),
        ("HEAT", "Canicule"),
        ("GENERAL", "Général"),
    ]
    SEVERITY_CHOICES = [
        ("LOW", "Faible"),
        ("MEDIUM", "Moyen"),
        ("HIGH", "Élevé"),
        ("CRITICAL", "Critique"),
    ]
    STATUS_CHOICES = [
        ("NEW", "Nouveau"),
        ("INVESTIGATING", "En cours"),
        ("CONFIRMED", "Confirmé"),
        ("RESOLVED", "Résolu"),
        ("DISMISSED", "Rejeté"),
    ]

    title = models.CharField(max_length=255)
    incident_type = models.CharField(max_length=32, choices=TYPE_CHOICES)
    description = models.TextField(blank=True)
    zone = models.ForeignKey("geography.MonitoringZone", on_delete=models.CASCADE, related_name="incidents")
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    severity = models.CharField(max_length=20, choices=SEVERITY_CHOICES, default="LOW")
    risk_score = models.FloatField(default=0.0)
    confidence_score = models.FloatField(default=0.0)
    source = models.CharField(max_length=128, blank=True)
    detected_at = models.DateTimeField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="NEW")
    assigned_to = models.ForeignKey("users.User", on_delete=models.SET_NULL, null=True, blank=True, related_name="incidents")
    anomaly = models.ForeignKey("anomalies.Anomaly", on_delete=models.SET_NULL, null=True, blank=True, related_name="incidents")
    is_simulated = models.BooleanField(default=False)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-detected_at"]
        indexes = [
            models.Index(fields=["-detected_at"]),
            models.Index(fields=["status", "severity"]),
        ]

    def __str__(self):
        return f"{self.title} ({self.get_severity_display()})"
