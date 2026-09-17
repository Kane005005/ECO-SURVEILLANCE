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
    region_number = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        help_text="Numéro officiel selon la loi de découpage administratif 2023 (1 à 19, ou 0 pour Bamako)"
    )
    capital = models.CharField(max_length=255, blank=True, help_text="Chef-lieu de la région")
    latitude = models.FloatField(null=True, blank=True, help_text="Latitude du chef-lieu")
    longitude = models.FloatField(null=True, blank=True, help_text="Longitude du chef-lieu")
    area_km2 = models.FloatField(null=True, blank=True)
    population = models.IntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["region_number", "name"]
        verbose_name = "Région Administrative"
        verbose_name_plural = "Régions Administratives"

    def __str__(self):
        if self.region_number:
            return f"Région {self.region_number:02d} - {self.name}"
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

class RegionalDirectorate(models.Model):
    """
    Direction Régionale opérationnelle ou de tutelle (DRPC, DRH, DREF, DRACPN, DRA, OTHER).
    Fournit les coordonnées cartographiques, contacts d'urgence (122) et rattachement régional.
    """
    DIRECTORATE_TYPES = [
        ("DRPC", "Direction Régionale de la Protection Civile"),
        ("DRH", "Direction Régionale de l'Hydraulique"),
        ("DREF", "Direction Régionale des Eaux et Forêts"),
        ("DRACPN", "Direction Régionale de l'Assainissement et du Contrôle des Pollutions et des Nuisances"),
        ("DRA", "Direction Régionale de l'Agriculture"),
        ("OTHER", "Autre Direction Régionale"),
    ]

    region = models.ForeignKey(
        Region,
        on_delete=models.CASCADE,
        related_name="directorates",
        help_text="Région administrative de compétence"
    )
    directorate_type = models.CharField(
        max_length=20,
        choices=DIRECTORATE_TYPES,
        default="DRPC",
        help_text="Spécialité ou domaine d'intervention"
    )
    name = models.CharField(max_length=255, help_text="Nom officiel du service régional")
    address = models.CharField(max_length=255, blank=True, help_text="Adresse ou quartier du siège régional")
    latitude = models.FloatField(help_text="Position GPS Latitude du siège")
    longitude = models.FloatField(help_text="Position GPS Longitude du siège")
    phone_primary = models.CharField(max_length=64, help_text="Ligne téléphonique standard")
    phone_secondary = models.CharField(max_length=64, blank=True, help_text="Ligne secondaire ou astreinte")
    emergency_number = models.CharField(max_length=32, default="122", help_text="Numéro d'urgence rapide (ex: 122)")
    email = models.EmailField(blank=True, help_text="Courriel officiel")
    is_active = models.BooleanField(default=True, help_text="Actif dans le plan de surveillance et d'alerte")
    notes = models.TextField(blank=True, help_text="Informations opérationnelles complémentaires")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["region", "directorate_type", "name"]
        verbose_name = "Direction Régionale"
        verbose_name_plural = "Directions Régionales"

    def __str__(self):
        return f"{self.name} ({self.region.name})"

    @property
    def icon_class(self):
        icons = {
            "DRPC": "fas fa-shield-halved",
            "DRH": "fas fa-droplet",
            "DREF": "fas fa-tree",
            "DRACPN": "fas fa-recycle",
            "DRA": "fas fa-wheat-awn",
            "OTHER": "fas fa-building",
        }
        return icons.get(self.directorate_type, "fas fa-building")

    @property
    def badge_color(self):
        colors = {
            "DRPC": "#DC2626",   # Rouge Protection Civile
            "DRH": "#0284C7",    # Bleu Cyan Hydraulique
            "DREF": "#16A34A",   # Vert Eaux & Forêts
            "DRACPN": "#059669", # Émeraude Assainissement
            "DRA": "#D97706",    # Ambre Agriculture
            "OTHER": "#475569",  # Slate
        }
        return colors.get(self.directorate_type, "#475569")

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
    competent_directorates = models.ManyToManyField(
        RegionalDirectorate,
        blank=True,
        related_name="assigned_zones",
        help_text="Directions spécifiques assignées à cette zone en plus des directions régionales"
    )
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

    def get_competent_directorates(self):
        """
        Résolution automatique des directions régionales compétentes pour la zone :
        Prend les directions de la région de rattachement (zone.region.directorates.all())
        combinées avec les assignations spécifiques directes.
        """
        if self.region:
            qs = self.region.directorates.filter(is_active=True)
            if self.competent_directorates.exists():
                return (qs | self.competent_directorates.filter(is_active=True)).distinct()
            return qs
        return self.competent_directorates.filter(is_active=True)
