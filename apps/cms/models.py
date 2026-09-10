from django.db import models
from django.utils.text import slugify
from django.utils import timezone


class BlogPost(models.Model):
    CATEGORY_CHOICES = [
        ("NEWS", "Actualités"),
        ("ECOLOGY", "Écologie & Biodiversité"),
        ("FLOOD_ALERT", "Alerte Inondation"),
        ("INNOVATION", "Innovation & Tech"),
    ]

    STATUS_CHOICES = [
        ("DRAFT", "Brouillon"),
        ("PUBLISHED", "Publié"),
    ]

    title = models.CharField(max_length=250, verbose_name="Titre")
    slug = models.SlugField(max_length=250, unique=True, blank=True)
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES, default="NEWS", verbose_name="Catégorie")
    summary = models.TextField(verbose_name="Résumé / Accroche")
    content = models.TextField(verbose_name="Contenu complet")
    cover_image = models.ImageField(upload_to="cms/blog/", blank=True, null=True, verbose_name="Image de couverture")
    cover_image_url = models.URLField(max_length=500, blank=True, default="", verbose_name="URL Image externe")
    author_name = models.CharField(max_length=100, default="Équipe ECO-SURVEILLANCE", verbose_name="Auteur")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="PUBLISHED", verbose_name="Statut")
    views_count = models.PositiveIntegerField(default=0, verbose_name="Vues")
    published_at = models.DateTimeField(null=True, blank=True, verbose_name="Date de publication")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-published_at", "-created_at"]
        verbose_name = "Article de Blog"
        verbose_name_plural = "Articles de Blog"

    def __str__(self):
        return f"[{self.get_category_display()}] {self.title}"

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.title) or f"article-{timezone.now().strftime('%Y%m%d%H%M%S')}"
            unique_slug = base_slug
            num = 1
            while BlogPost.objects.filter(slug=unique_slug).exclude(pk=self.pk).exists():
                unique_slug = f"{base_slug}-{num}"
                num += 1
            self.slug = unique_slug
        if self.status == "PUBLISHED" and not self.published_at:
            self.published_at = timezone.now()
        super().save(*args, **kwargs)

    @property
    def image_display_url(self):
        if self.cover_image:
            return self.cover_image.url
        if self.cover_image_url:
            return self.cover_image_url
        # Category specific fallback image
        fallbacks = {
            "NEWS": "https://images.unsplash.com/photo-1504384308090-c894fdcc538d?w=800&q=80",
            "ECOLOGY": "https://images.unsplash.com/photo-1448375240586-882707db888b?w=800&q=80",
            "FLOOD_ALERT": "https://images.unsplash.com/photo-1547683905-f686c993aae5?w=800&q=80",
            "INNOVATION": "https://images.unsplash.com/photo-1518770660439-4636190af475?w=800&q=80",
        }
        return fallbacks.get(self.category, "https://images.unsplash.com/photo-1500530855697-b586d89ba3ee?w=800&q=80")


class ProjectPortfolio(models.Model):
    CATEGORY_CHOICES = [
        ("SURVEILLANCE", "Surveillance Spatiale"),
        ("HYDROLOGIE", "Modélisation Hydrologique"),
        ("AI_PREDICTION", "Intelligence Artificielle & IA"),
        ("COMMUNAUTE", "Alerte & Mobilisation"),
        ("BIODIVERSITE", "Biodiversité & Forêts"),
    ]

    title = models.CharField(max_length=250, verbose_name="Titre du projet")
    slug = models.SlugField(max_length=250, unique=True, blank=True)
    subtitle = models.CharField(max_length=250, blank=True, default="", verbose_name="Sous-titre")
    category = models.CharField(max_length=100, choices=CATEGORY_CHOICES, default="SURVEILLANCE", verbose_name="Catégorie")
    description = models.TextField(verbose_name="Description du projet")
    cover_image = models.ImageField(upload_to="cms/portfolio/", blank=True, null=True, verbose_name="Image de couverture")
    cover_image_url = models.URLField(max_length=500, blank=True, default="", verbose_name="URL Image externe")
    partner_or_client = models.CharField(max_length=200, blank=True, default="", verbose_name="Partenaire / Client")
    technologies_used = models.CharField(
        max_length=250,
        default="Google Earth Engine, Sentinel-2, GloFAS, Django, Leaflet",
        verbose_name="Technologies utilisées"
    )
    demo_url = models.URLField(max_length=500, blank=True, default="", verbose_name="Lien Démo / En savoir plus")
    is_featured = models.BooleanField(default=False, verbose_name="Projet mis en avant")
    completion_date = models.DateField(null=True, blank=True, verbose_name="Date de finalisation")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-is_featured", "-completion_date", "-created_at"]
        verbose_name = "Projet Réalisé"
        verbose_name_plural = "Portfolio Projets"

    def __str__(self):
        return f"{self.title} ({self.get_category_display()})"

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.title) or f"projet-{timezone.now().strftime('%Y%m%d%H%M%S')}"
            unique_slug = base_slug
            num = 1
            while ProjectPortfolio.objects.filter(slug=unique_slug).exclude(pk=self.pk).exists():
                unique_slug = f"{base_slug}-{num}"
                num += 1
            self.slug = unique_slug
        super().save(*args, **kwargs)

    @property
    def image_display_url(self):
        if self.cover_image:
            return self.cover_image.url
        if self.cover_image_url:
            return self.cover_image_url
        return "https://images.unsplash.com/photo-1518770660439-4636190af475?w=800&q=80"


class SiteSettings(models.Model):
    """
    Singleton model for global site configuration, branding, contacts, and emergency alert banners.
    """
    ALERT_LEVEL_CHOICES = [
        ("INFO", "Information (Bleu)"),
        ("WARNING", "Vigilance (Jaune/Orange)"),
        ("DANGER", "Danger / Alerte (Rouge)"),
        ("CRITICAL", "Urgence Absolue (Violet/Noir)"),
    ]

    site_name = models.CharField(max_length=150, default="ECO-SURVEILLANCE MALI", verbose_name="Nom de la plateforme")
    site_tagline = models.CharField(
        max_length=255,
        default="Plateforme Nationale de Surveillance Environnementale & Hydrologique",
        verbose_name="Slogan / Sous-titre"
    )
    contact_email = models.EmailField(default="contact@eco-surveillance.ml", verbose_name="Email de contact")
    contact_phone = models.CharField(max_length=50, default="+223 20 22 00 00", verbose_name="Téléphone fixe")
    whatsapp_phone = models.CharField(max_length=50, default="+223 70 00 00 00", verbose_name="WhatsApp")
    emergency_line = models.CharField(max_length=50, default="80 00 11 22", verbose_name="Numéro d'urgence vert")
    headquarters_address = models.CharField(
        max_length=255,
        default="Bamako, Mali — Cité Administrative, Bâtiment Numérique",
        verbose_name="Adresse du siège"
    )
    facebook_url = models.URLField(max_length=255, blank=True, default="", verbose_name="Facebook")
    twitter_url = models.URLField(max_length=255, blank=True, default="", verbose_name="X / Twitter")
    linkedin_url = models.URLField(max_length=255, blank=True, default="", verbose_name="LinkedIn")
    github_url = models.URLField(max_length=255, blank=True, default="", verbose_name="GitHub")
    alert_banner_active = models.BooleanField(default=False, verbose_name="Activer le bandeau d'alerte national")
    alert_banner_text = models.CharField(max_length=300, blank=True, default="", verbose_name="Texte du bandeau")
    alert_banner_level = models.CharField(
        max_length=20,
        choices=ALERT_LEVEL_CHOICES,
        default="WARNING",
        verbose_name="Niveau de gravité du bandeau"
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Paramètres du Site"
        verbose_name_plural = "Paramètres du Site"

    def __str__(self):
        return f"{self.site_name} (Configuration générale)"

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def get_settings(cls):
        obj, _ = cls.objects.get_or_create(
            pk=1,
            defaults={
                "site_name": "ECO-SURVEILLANCE MALI",
                "site_tagline": "Plateforme Nationale de Surveillance Environnementale & Hydrologique",
                "contact_email": "contact@eco-surveillance.ml",
                "contact_phone": "+223 20 22 00 00",
                "whatsapp_phone": "+223 70 00 00 00",
                "emergency_line": "80 00 11 22",
                "headquarters_address": "Bamako, Mali — Cité Administrative, Bâtiment Numérique",
                "alert_banner_active": False,
                "alert_banner_text": "",
                "alert_banner_level": "WARNING",
            }
        )
        return obj
