from django.db import models

class Alert(models.Model):
    CHANNEL_CHOICES = [
        ("WEB", "Web"),
        ("EMAIL", "Email"),
    ]
    SEVERITY_CHOICES = [
        ("LOW", "Faible"),
        ("MEDIUM", "Moyen"),
        ("HIGH", "Élevé"),
        ("CRITICAL", "Critique"),
    ]
    STATUS_CHOICES = [
        ("PENDING", "En attente"),
        ("SENT", "Envoyé"),
        ("READ", "Lu"),
        ("FAILED", "Échoué"),
    ]

    incident = models.ForeignKey("incidents.Incident", on_delete=models.CASCADE, related_name="alerts")
    recipient = models.ForeignKey("users.User", on_delete=models.CASCADE, related_name="alerts")
    channel = models.CharField(max_length=16, choices=CHANNEL_CHOICES, default="WEB")
    severity = models.CharField(max_length=20, choices=SEVERITY_CHOICES, default="MEDIUM")
    message = models.TextField()
    sent_at = models.DateTimeField(null=True, blank=True)
    read_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default="PENDING")
    is_simulated = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status", "severity"]),
        ]

    def __str__(self):
        return f"Alert {self.get_severity_display()} - {self.incident.title}"
