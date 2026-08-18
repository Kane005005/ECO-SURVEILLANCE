from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    ROLE_CHOICES = [
        ("viewer", "Observateur"),
        ("analyst", "Analyste"),
        ("operator", "Opérateur"),
        ("administrator", "Administrateur"),
    ]
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default="viewer")
    phone = models.CharField(max_length=20, blank=True)
    organization = models.CharField(max_length=255, blank=True)

    class Meta:
        verbose_name = "Utilisateur"
        verbose_name_plural = "Utilisateurs"

    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"

    @property
    def is_administrator(self):
        return self.role == "administrator"

    @property
    def is_analyst(self):
        return self.role in ("analyst", "operator", "administrator")
