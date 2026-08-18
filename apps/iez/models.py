from django.db import models

class IEZCalculation(models.Model):
    STATUS_CHOICES = [
        ("BON", "Bon état"),
        ("VIGILANCE", "Vigilance"),
        ("DEGRADÉ", "Dégradé"),
        ("CRITIQUE", "Critique"),
    ]

    zone = models.ForeignKey("geography.MonitoringZone", on_delete=models.CASCADE, related_name="iez_calculations")
    score = models.FloatField(default=0.0, help_text="0-100")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="DEGRADÉ")
    components = models.JSONField(default=dict, blank=True)
    weights = models.JSONField(default=dict, blank=True)
    algorithm_version = models.CharField(max_length=32, default="1.0")
    calculated_at = models.DateTimeField()
    is_simulated = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-calculated_at"]
        verbose_name = "Calcul IEZ"
        verbose_name_plural = "Calculs IEZ"
        indexes = [
            models.Index(fields=["zone", "-calculated_at"]),
        ]

    def __str__(self):
        return f"IEZ {self.score} - {self.zone.name} ({self.status})"
