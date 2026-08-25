from django.core.management.base import BaseCommand
from django.utils import timezone
from apps.reports.models import FieldReport


class Command(BaseCommand):
    help = "Seed initial realistic field reports (crowdsourcing observations) across Mali."

    def handle(self, *args, **options):
        initial_reports = [
            {
                "latitude": 14.4958,
                "longitude": -4.1856,
                "report_type": "FLOOD",
                "severity": "HIGH",
                "title": "Montée rapide du niveau au port fluvial de Mopti",
                "description": "Le niveau du fleuve a atteint le quai piétonnier. Les bateliers signalent un courant soutenu depuis 48h.",
                "author_name": "Oumar Cissé (Pêcheur Mopti)",
                "author_phone": "+223 76 12 34 56",
                "is_verified": True,
            },
            {
                "latitude": 12.8628,
                "longitude": -7.5598,
                "report_type": "WATER_QUALITY",
                "severity": "MEDIUM",
                "title": "Turbidité anormale et dépôts près de Koulikoro",
                "description": "Coloration brunâtre constatée le long des berges aval. Débit ralenti et présence de résidus de dragage.",
                "author_name": "Fatoumata Diarra (Agent Eaux & Forêts)",
                "author_phone": "+223 65 98 74 12",
                "is_verified": True,
            },
            {
                "latitude": 13.4317,
                "longitude": -6.2157,
                "report_type": "DROUGHT",
                "severity": "MEDIUM",
                "title": "Baisse du niveau des mares à Ségou Markala",
                "description": "Les canaux secondaires du barrage affichent un étiage précoce impactant les cultures maraîchères locales.",
                "author_name": "Amadou Koné (Agriculteur)",
                "author_phone": "+223 70 45 89 21",
                "is_verified": False,
            },
            {
                "latitude": 16.2717,
                "longitude": -0.0447,
                "report_type": "WILDFIRE",
                "severity": "CRITICAL",
                "title": "Feu de pâturage actif au sud de Gao",
                "description": "Foyer attisé par un vent d'Est modéré menaçant les zones d'embouche bovine. Intervention communautaire en cours.",
                "author_name": "Ibrahim Maïga (Éleveur)",
                "author_phone": "+223 82 33 11 00",
                "is_verified": True,
            },
            {
                "latitude": 12.6392,
                "longitude": -8.0029,
                "report_type": "OTHER",
                "severity": "LOW",
                "title": "Dépôt d'encombrants sur la berge du fleuve à Bamako",
                "description": "Accumulation de déchets plastiques à proximité du pont des Martyrs risquant d'obstruer l'évacuation pluviale.",
                "author_name": "Association Jeunesse Éco Bamako",
                "author_phone": "+223 66 11 22 33",
                "is_verified": False,
            }
        ]

        created_count = 0
        for r_data in initial_reports:
            obj, created = FieldReport.objects.get_or_create(
                title=r_data["title"],
                defaults=r_data
            )
            if created:
                created_count += 1

        self.stdout.write(self.style.SUCCESS(f"Successfully seeded {created_count} field reports."))
