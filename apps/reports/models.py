from django.db import models


class Report(models.Model):
    REPORT_TYPES = [
        ("DAILY", "Quotidien"),
        ("WEEKLY", "Hebdomadaire"),
        ("MONTHLY", "Mensuel"),
        ("INCIDENT", "Incident"),
        ("ZONE", "Zone"),
    ]
    report_type = models.CharField(max_length=16, choices=REPORT_TYPES)
    title = models.CharField(max_length=255)
    zone = models.ForeignKey("geography.MonitoringZone", on_delete=models.SET_NULL, null=True, blank=True, related_name="reports")
    content = models.TextField(blank=True)
    data = models.JSONField(default=dict, blank=True)
    generated_at = models.DateTimeField(auto_now_add=True)
    is_simulated = models.BooleanField(default=False)

    class Meta:
        ordering = ["-generated_at"]

    def __str__(self):
        return f"{self.get_report_type_display()}: {self.title}"


class FieldReport(models.Model):
    """
    Signalement terrain géoréférencé participatif (Crowdsourcing / Remontées agents).
    """
    REPORT_TYPE_CHOICES = [
        ("FLOOD", "Inondation / Crue"),
        ("WILDFIRE", "Feu de brousse / Incendie"),
        ("DROUGHT", "Sécheresse / Puits tari"),
        ("WATER_QUALITY", "Pollution eau / Fleuve"),
        ("OTHER", "Autre anomalie écologique"),
    ]

    SEVERITY_CHOICES = [
        ("LOW", "Faible"),
        ("MEDIUM", "Modéré"),
        ("HIGH", "Élevé"),
        ("CRITICAL", "Urgence critique"),
    ]

    latitude = models.FloatField(help_text="Latitude WGS84")
    longitude = models.FloatField(help_text="Longitude WGS84")
    report_type = models.CharField(max_length=30, choices=REPORT_TYPE_CHOICES, default="OTHER")
    severity = models.CharField(max_length=20, choices=SEVERITY_CHOICES, default="MEDIUM")
    title = models.CharField(max_length=150, help_text="Titre court de l'observation")
    description = models.TextField(help_text="Détail du constat terrain")
    author_name = models.CharField(max_length=100, default="Anonyme", help_text="Nom de l'observateur ou agent")
    author_phone = models.CharField(max_length=30, blank=True, default="", help_text="Contact téléphonique optionnel")
    is_verified = models.BooleanField(default=False, help_text="Validation par un expert ou modérateur")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Signalement Terrain"
        verbose_name_plural = "Signalements Terrain"

    def __str__(self):
        return f"[{self.get_severity_display()}] {self.get_report_type_display()} - {self.title} ({self.created_at.strftime('%d/%m/%Y')})"

    def to_geojson_feature(self):
        return {
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [self.longitude, self.latitude]
            },
            "properties": {
                "id": self.id,
                "title": self.title,
                "description": self.description,
                "report_type": self.report_type,
                "report_type_display": self.get_report_type_display(),
                "severity": self.severity,
                "severity_display": self.get_severity_display(),
                "author_name": self.author_name,
                "author_phone": self.author_phone,
                "is_verified": self.is_verified,
                "created_at": self.created_at.isoformat(),
                "created_at_display": self.created_at.strftime("%d/%m/%Y %H:%M"),
            }
        }

