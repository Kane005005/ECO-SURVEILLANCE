from django.db import models

class Country(models.Model):
    name = models.CharField(max_length=255)
    code = models.CharField(max_length=10, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

class Region(models.Model):
    country = models.ForeignKey(Country, on_delete=models.CASCADE, related_name="regions")
    name = models.CharField(max_length=255)
    code = models.CharField(max_length=50, unique=True)
    capital = models.CharField(max_length=255, blank=True)
    area_km2 = models.FloatField(null=True, blank=True)
    population = models.IntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

class Circle(models.Model):
    region = models.ForeignKey(Region, on_delete=models.CASCADE, related_name="circles")
    name = models.CharField(max_length=255)
    code = models.CharField(max_length=50, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

class Commune(models.Model):
    circle = models.ForeignKey(Circle, on_delete=models.CASCADE, related_name="communes")
    name = models.CharField(max_length=255)
    code = models.CharField(max_length=50, unique=True)
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

class MonitoringZone(models.Model):
    ZONE_TYPES = [
        ("URBAN", "Urbain"),
        ("AGRICULTURAL", "Agricole"),
        ("FOREST", "Forêt"),
        ("SAVANNAH", "Savane"),
        ("WETLAND", "Zone humide"),
        ("DESERT", "Désert"),
        ("RIVER", "Cours d'eau"),
        ("LAKE", "Lac"),
    ]
    STATUS_CHOICES = [
        ("MONITORING", "Surveillance"),
        ("ALERT", "Alerte"),
        ("CRITICAL", "Critique"),
        ("NORMAL", "Normal"),
    ]
    VULNERABILITY_CHOICES = [
        ("LOW", "Faible"),
        ("MEDIUM", "Moyen"),
        ("HIGH", "Élevé"),
        ("CRITICAL", "Critique"),
    ]

    name = models.CharField(max_length=255)
    zone_type = models.CharField(max_length=32, choices=ZONE_TYPES)
    region = models.ForeignKey(Region, on_delete=models.SET_NULL, null=True, blank=True, related_name="zones")
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    area_km2 = models.FloatField(null=True, blank=True)
    population = models.IntegerField(null=True, blank=True)
    vulnerability_level = models.CharField(max_length=20, choices=VULNERABILITY_CHOICES, default="MEDIUM")
    current_iez = models.FloatField(default=50.0)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="MONITORING")
    is_simulated = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} ({self.get_zone_type_display()})"
