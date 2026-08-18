from django.db import models

class RiskAssessment(models.Model):
    RISK_TYPES = [
        ("WILDFIRE", "Feu de forêt"),
        ("DROUGHT", "Sécheresse"),
        ("VEGETATION_DEGRADATION", "Dégradation végétale"),
        ("WATER_POLLUTION", "Pollution eau"),
        ("WATER_STRESS", "Stress hydrique"),
        ("ATMOSPHERIC_ANOMALY", "Anomalie atmosphérique"),
        ("HEAT", "Canicule"),
        ("ENVIRONMENTAL_GENERAL", "Risque général"),
    ]
    LEVEL_CHOICES = [
        ("GREEN", "Normal"),
        ("YELLOW", "Vigilance"),
        ("ORANGE", "Risque élevé"),
        ("RED", "Danger critique"),
    ]
    SEVERITY_CHOICES = [
        ("LOW", "Faible"),
        ("MEDIUM", "Moyen"),
        ("HIGH", "Élevé"),
        ("CRITICAL", "Critique"),
    ]

    zone = models.ForeignKey("geography.MonitoringZone", on_delete=models.CASCADE, related_name="risk_assessments")
    risk_type = models.CharField(max_length=32, choices=RISK_TYPES)
    risk_score = models.FloatField(default=0.0, help_text="0-100")
    confidence_score = models.FloatField(default=0.0, help_text="0-100")
    level = models.CharField(max_length=16, choices=LEVEL_CHOICES, default="GREEN")
    severity = models.CharField(max_length=20, choices=SEVERITY_CHOICES, default="LOW")
    factors = models.JSONField(default=list, blank=True)
    algorithm_version = models.CharField(max_length=32, default="1.0")
    calculated_at = models.DateTimeField()
    is_simulated = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-calculated_at"]
        indexes = [
            models.Index(fields=["zone", "risk_type", "-calculated_at"]),
        ]

    def __str__(self):
        return f"{self.get_risk_type_display()} - {self.zone.name} ({self.get_level_display()})"
