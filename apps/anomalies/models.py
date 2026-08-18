from django.db import models

class Anomaly(models.Model):
    TYPE_CHOICES = [
        ("VEGETATION", "Végétation"),
        ("WATER", "Eau"),
        ("FIRE", "Feu"),
        ("CLIMATE", "Climat"),
        ("ATMOSPHERE", "Atmosphère"),
        ("MULTI_SIGNAL", "Multi-signal"),
    ]
    SEVERITY_CHOICES = [
        ("LOW", "Faible"),
        ("MEDIUM", "Moyen"),
        ("HIGH", "Élevé"),
        ("CRITICAL", "Critique"),
    ]
    STATUS_CHOICES = [
        ("NEW", "Nouveau"),
        ("INVESTIGATING", "En cours d'investigation"),
        ("CONFIRMED", "Confirmé"),
        ("RESOLVED", "Résolu"),
        ("DISMISSED", "Rejeté"),
    ]

    anomaly_type = models.CharField(max_length=32, choices=TYPE_CHOICES)
    zone = models.ForeignKey("geography.MonitoringZone", on_delete=models.CASCADE, related_name="anomalies")
    source = models.CharField(max_length=128)
    detected_at = models.DateTimeField()
    severity = models.CharField(max_length=20, choices=SEVERITY_CHOICES, default="LOW")
    score = models.FloatField(default=0.0, help_text="0-100 anomaly score")
    confidence = models.FloatField(default=0.0, help_text="0-1 confidence")
    metric = models.CharField(max_length=128, blank=True)
    current_value = models.FloatField(null=True, blank=True)
    baseline_value = models.FloatField(null=True, blank=True)
    z_score = models.FloatField(null=True, blank=True)
    description = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="NEW")
    is_simulated = models.BooleanField(default=False)
    data = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-detected_at"]
        indexes = [
            models.Index(fields=["-detected_at"]),
            models.Index(fields=["zone", "anomaly_type"]),
        ]

    def __str__(self):
        return f"{self.get_anomaly_type_display()} - {self.zone.name} ({self.severity})"
