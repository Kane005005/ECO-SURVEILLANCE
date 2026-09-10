from django.core.management.base import BaseCommand
from django.utils import timezone
from apps.cms.models import BlogPost, ProjectPortfolio, SiteSettings


class Command(BaseCommand):
    help = "Seed initial CMS blog posts, portfolio projects, and site settings."

    def handle(self, *args, **options):
        # 1. Site Settings
        settings = SiteSettings.get_settings()
        self.stdout.write(self.style.SUCCESS(f"Site Settings verified: {settings.site_name}"))

        # 2. Blog Posts
        if not BlogPost.objects.exists():
            BlogPost.objects.create(
                title="Surveillance Spatiale du Delta Intérieur du Niger : Déploiement Sentinel-2 & GEE",
                slug="surveillance-spatiale-delta-interieur-niger",
                category="ECOLOGY",
                summary="Intégration des composites Sentinel-2 L2A harmonisés via Google Earth Engine pour le suivi de la canopée et des zones humides.",
                content="""Le Delta Intérieur du Niger constitue l'un des écosystèmes les plus vitaux d'Afrique de l'Ouest. Grâce à l'intégration directe de Google Earth Engine (GEE) et de la constellation Copernicus Sentinel-2, la plateforme ECO-SURVEILLANCE MALI calcule désormais en continu les indices foliaires NDVI et d'humidité NDMI à 10 et 20 mètres de résolution.

Cette capacité permet aux agents des Eaux & Forêts et aux gestionnaires territoriaux d'identifier en amont le stress hydrique des forêts classées et le recul du couvert végétal sous l'effet du changement climatique.""",
                author_name="Dr. Ousmane Traoré (Télédétection)",
                status="PUBLISHED",
                views_count=142,
                cover_image_url="https://images.unsplash.com/photo-1448375240586-882707db888b?w=1000&q=80",
                published_at=timezone.now(),
            )

            BlogPost.objects.create(
                title="Anticipation des Crues Fluviales : Modélisation GloFAS & Diagnostic IA GPT-OSS",
                slug="anticipation-crues-fluviales-glofas-gpt-oss",
                category="FLOOD_ALERT",
                summary="Comment la corrélation multi-sources entre GloFAS, LANCE Flood et l'IA générative permet d'anticiper les risques de submersion à 72 heures.",
                content="""Face aux inondations récurrentes le long de l'axe hydrologique Koulikoro - Ségou - Mopti - Diré, ECO-SURVEILLANCE combine les prévisions d'écoulement du Copernicus Emergency Management Service (GloFAS) avec les observations d'eau de surface en temps quasi réel issues des capteurs VIIRS/MODIS.

Le moteur corrélatif ECO-Engine transmet automatiquement les séries chronologiques de débit au modèle GPT-OSS, qui produit des recommandations d'évacuation préventive et de gestion des barrages en français clair.""",
                author_name="Aminata Coulibaly (Hydrologue)",
                status="PUBLISHED",
                views_count=218,
                cover_image_url="https://images.unsplash.com/photo-1547683905-f686c993aae5?w=1000&q=80",
                published_at=timezone.now(),
            )

            BlogPost.objects.create(
                title="Mobilisation Citoyenne : Le Rôle Clé des Remontées Terrain Géoréférencées",
                slug="mobilisation-citoyenne-remontees-terrain",
                category="INNOVATION",
                summary="Le module participatif permet aux communautés rurales de transmettre instantanément des signalements avec géolocalisation GPS.",
                content="""La télédétection par satellite gagne en précision lorsqu'elle est combinée aux observations de terrain. Avec le nouveau module de signalement cartographique, tout observateur, chef de village ou agent local peut documenter un feu de brousse, un assèchement de puits ou une pollution de cours d'eau en 3 clics, même depuis un smartphone basique.

Chaque alerte est immédiatement géolocalisée et intégrée à la couche participative pour validation rapide.""",
                author_name="Mamadou Keita (Engagement Communautaire)",
                status="PUBLISHED",
                views_count=97,
                cover_image_url="https://images.unsplash.com/photo-1518770660439-4636190af475?w=1000&q=80",
                published_at=timezone.now(),
            )
            self.stdout.write(self.style.SUCCESS("Created 3 initial blog posts."))

        # 3. Portfolio Projects
        if not ProjectPortfolio.objects.exists():
            ProjectPortfolio.objects.create(
                title="Réseau Sentinelle Hydrologique du Fleuve Niger",
                slug="reseau-sentinelle-hydrologique-fleuve-niger",
                subtitle="Système d'alerte précoce aux crues et inondations pour 8 stations fluviales majeures",
                category="HYDROLOGIE",
                description="Déploiement d'un pipeline complet de données hydrologiques temps réel intégrant les prévisions GloFAS EWDS à 72 heures, le calcul de tendances dynamiques, et l'alerte multi-seuils (Vigilance, Alerte, Danger).",
                partner_or_client="Direction Nationale de l'Hydraulique (DNH Mali)",
                technologies_used="Copernicus GloFAS, Python, Django, Leaflet, Chart.js, Redis",
                demo_url="/map/",
                is_featured=True,
                cover_image_url="https://images.unsplash.com/photo-1500530855697-b586d89ba3ee?w=1000&q=80",
            )

            ProjectPortfolio.objects.create(
                title="Cartographie Forestière et Canopée Haute Résolution via GEE",
                slug="cartographie-forestiere-canopee-gee",
                subtitle="Surveillance multi-temporelle de la biomasse et détection des coupes illégales",
                category="SURVEILLANCE",
                description="Calcul automatisé des indices de végétation NDVI et teneur en eau foliaire NDMI à partir des tuiles Sentinel-2 Harmonized L2A dans Google Earth Engine. Statistiques zonales instantanées par polygone.",
                partner_or_client="Direction Nationale des Eaux et Forêts",
                technologies_used="Google Earth Engine (GEE), Sentinel-2, Redis XYZ Cache, GeoJSON",
                demo_url="/map/",
                is_featured=True,
                cover_image_url="https://images.unsplash.com/photo-1448375240586-882707db888b?w=1000&q=80",
            )

            ProjectPortfolio.objects.create(
                title="Copilote Écologique et Décisionnel IA GPT-OSS 120B",
                slug="copilote-ecologique-ia-gpt-oss",
                subtitle="Assistant conversationnel génératif pour l'interprétation des anomalies environnementales",
                category="AI_PREDICTION",
                description="Agent d'intelligence artificielle contextuel capable d'interroger les bases satellitaires et météorologiques pour synthétiser des diagnostics environnementaux et orienter les secours d'urgence.",
                partner_or_client="Ministère de l'Environnement, de l'Assainissement et du Développement Durable",
                technologies_used="Groq, GPT-OSS 120B, LangChain/LlamaIndex, OpenAI Compatible API",
                demo_url="/dashboard/",
                is_featured=False,
                cover_image_url="https://images.unsplash.com/photo-1518770660439-4636190af475?w=1000&q=80",
            )
            self.stdout.write(self.style.SUCCESS("Created 3 initial portfolio projects."))
