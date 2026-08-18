from django.db import models


class DataSource(models.Model):
    SOURCE_TYPES = [
        ("SATELLITE", "Satellite"),
        ("CLIMATE", "Climat"),
        ("ATMOSPHERE", "Atmosphère"),
        ("FIRE", "Feu"),
        ("WATER", "Eau"),
        ("SENSOR", "Capteur"),
        ("AI", "IA"),
    ]
    STATUS_CHOICES = [
        ("ACTIVE", "Active"),
        ("DEGRADED", "Dégradée"),
        ("OFFLINE", "Hors ligne"),
        ("NOT_CONFIGURED", "Non configurée"),
    ]

    name = models.CharField(max_length=255)
    provider = models.CharField(max_length=128)
    source_type = models.CharField(max_length=32, choices=SOURCE_TYPES)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    is_simulated = models.BooleanField(default=False)
    last_sync = models.DateTimeField(null=True, blank=True)
    configuration = models.JSONField(default=dict, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="NOT_CONFIGURED")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} ({self.provider})"
