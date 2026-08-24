from django.db import models


class WaterBody(models.Model):
    BODY_TYPES = [
        ("RIVER", "Rivière"),
        ("LAKE", "Lac"),
        ("RESERVOIR", "Réservoir"),
        ("POND", "Mare"),
        ("DAM", "Barrage"),
    ]
    name = models.CharField(max_length=255)
    body_type = models.CharField(max_length=32, choices=BODY_TYPES)
    zone = models.ForeignKey(
        "geography.MonitoringZone",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="water_bodies",
    )
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    area_km2 = models.FloatField(null=True, blank=True)
    is_simulated = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.get_body_type_display()})"


class WaterObservation(models.Model):
    METRIC_CHOICES = [
        ("TEMPERATURE", "Température"),
        ("PH", "pH"),
        ("TURBIDITY", "Turbidité"),
        ("CONDUCTIVITY", "Conductivité"),
        ("DISSOLVED_OXYGEN", "Oxygène dissous"),
        ("WATER_LEVEL", "Niveau d'eau"),
    ]
    water_body = models.ForeignKey(WaterBody, on_delete=models.CASCADE, related_name="observations")
    metric = models.CharField(max_length=32, choices=METRIC_CHOICES)
    value = models.FloatField()
    unit = models.CharField(max_length=32, blank=True)
    baseline_value = models.FloatField(null=True, blank=True)
    std_dev = models.FloatField(null=True, blank=True)
    measured_at = models.DateTimeField()
    source = models.CharField(max_length=128, default="Sensor")
    is_simulated = models.BooleanField(default=False)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-measured_at"]
        indexes = [
            models.Index(fields=["water_body", "metric", "-measured_at"]),
        ]

    def __str__(self):
        return f"{self.metric}={self.value} in {self.water_body.name}"


class HydrologicalStation(models.Model):
    """Station hydrologique opérationnelle sur les cours d'eau maliens."""
    RIVER_CHOICES = [
        ("Niger", "Fleuve Niger"),
        ("Sénégal", "Fleuve Sénégal"),
        ("Bani", "Rivière Bani"),
        ("Bakoye", "Rivière Bakoye"),
        ("Bafing", "Rivière Bafing"),
        ("Sankarani", "Rivière Sankarani"),
    ]

    nom = models.CharField(max_length=255)
    cours_d_eau = models.CharField(max_length=64, default="Niger")
    latitude = models.FloatField(help_text="Latitude administrative / géographique")
    longitude = models.FloatField(help_text="Longitude administrative / géographique")
    latitude_river = models.FloatField(null=True, blank=True, help_text="Latitude recalée sur chenal GloFAS")
    longitude_river = models.FloatField(null=True, blank=True, help_text="Longitude recalée sur chenal GloFAS")
    seuil_vigilance = models.FloatField(default=1000.0, help_text="Débit seuil de vigilance (m3/s)")
    seuil_alerte = models.FloatField(default=2000.0, help_text="Débit seuil d'alerte crue (m3/s)")
    seuil_danger = models.FloatField(default=3000.0, help_text="Débit seuil de danger imminent (m3/s)")
    is_active = models.BooleanField(default=True)
    zone = models.ForeignKey(
        "geography.MonitoringZone",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="hydrological_stations",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["nom"]
        verbose_name = "Station hydrologique"
        verbose_name_plural = "Stations hydrologiques"

    @property
    def name(self):
        return self.nom

    @property
    def river(self):
        return self.cours_d_eau

    def __str__(self):
        return f"{self.nom} ({self.cours_d_eau})"


class RiverForecast(models.Model):
    """Prévisions hydrologiques de débit GloFAS (24h, 48h, 72h)."""
    ALERT_LEVELS = [
        ("GREEN", "Normal / Vert"),
        ("YELLOW", "Vigilance / Jaune"),
        ("ORANGE", "Alerte / Orange"),
        ("RED", "Danger / Rouge"),
    ]

    station = models.ForeignKey(
        HydrologicalStation,
        on_delete=models.CASCADE,
        related_name="forecasts",
    )
    date_run = models.DateField(help_text="Date du run opérationnel GloFAS")
    leadtime_hours = models.IntegerField(help_text="Échéance de prévision (24, 48, 72)")
    discharge_m3s = models.FloatField(help_text="Débit prévu en m3/s")
    trend_72h_pct = models.FloatField(default=0.0, help_text="Pourcentage de variation de tendance à 72h")
    alert_level = models.CharField(max_length=16, choices=ALERT_LEVELS, default="GREEN")
    is_simulated = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-date_run", "station", "leadtime_hours"]
        indexes = [
            models.Index(fields=["station", "-date_run", "leadtime_hours"]),
            models.Index(fields=["alert_level"]),
        ]
        verbose_name = "Prévision de débit"
        verbose_name_plural = "Prévisions de débit"

    def __str__(self):
        return f"{self.station.nom} [J+{self.leadtime_hours//24}] : {self.discharge_m3s:.1f} m3/s ({self.alert_level})"


class FloodObservation(models.Model):
    """Observations satellitaires des inondations (NASA LANCE VIIRS NRT3)."""
    zone = models.ForeignKey(
        "geography.MonitoringZone",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="flood_observations",
    )
    tile_name = models.CharField(max_length=32, help_text="Tuile MODAPS ex: h16v07, h17v07")
    observation_date = models.DateField(help_text="Date d'observation satellitaire")
    flooded_area_km2 = models.FloatField(default=0.0, help_text="Superficie inondée totale en km2")
    flooded_pixels_count = models.IntegerField(default=0, help_text="Nombre de pixels inondés (classe 3)")
    flood_geojson = models.JSONField(default=dict, blank=True, help_text="GeoJSON FeatureCollection des centroïdes / emprises")
    source = models.CharField(max_length=128, default="NASA LANCE VIIRS")
    is_simulated = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-observation_date", "tile_name"]
        indexes = [
            models.Index(fields=["-observation_date", "tile_name"]),
        ]
        verbose_name = "Observation d'inondation"
        verbose_name_plural = "Observations d'inondation"

    def __str__(self):
        return f"Flood {self.tile_name} ({self.observation_date}): {self.flooded_area_km2:.2f} km²"
