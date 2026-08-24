from django.core.management.base import BaseCommand
from apps.water.models import HydrologicalStation
from apps.geography.models import MonitoringZone


class Command(BaseCommand):
    help = "Seed key hydrological stations of Mali (Bamako, Koulikoro, Ségou, Mopti, Diré, Gao)"

    def handle(self, *args, **options):
        stations_data = [
            {
                "nom": "Bamako",
                "cours_d_eau": "Niger",
                "latitude": 12.6392,
                "longitude": -8.0029,
                "latitude_river": 12.6380,
                "longitude_river": -8.0010,
                "seuil_vigilance": 1200.0,
                "seuil_alerte": 2200.0,
                "seuil_danger": 3200.0,
                "zone_name": "Bamako",
            },
            {
                "nom": "Koulikoro",
                "cours_d_eau": "Niger",
                "latitude": 12.8627,
                "longitude": -7.5599,
                "latitude_river": 12.8610,
                "longitude_river": -7.5580,
                "seuil_vigilance": 1300.0,
                "seuil_alerte": 2400.0,
                "seuil_danger": 3500.0,
                "zone_name": "Koulikoro",
            },
            {
                "nom": "Ségou",
                "cours_d_eau": "Niger",
                "latitude": 13.4317,
                "longitude": -6.2625,
                "latitude_river": 13.4350,
                "longitude_river": -6.2600,
                "seuil_vigilance": 1400.0,
                "seuil_alerte": 2500.0,
                "seuil_danger": 3600.0,
                "zone_name": "Ségou",
            },
            {
                "nom": "Mopti",
                "cours_d_eau": "Niger",
                "latitude": 14.4958,
                "longitude": -4.1856,
                "latitude_river": 14.4980,
                "longitude_river": -4.1820,
                "seuil_vigilance": 1600.0,
                "seuil_alerte": 2800.0,
                "seuil_danger": 4000.0,
                "zone_name": "Mopti",
            },
            {
                "nom": "Diré",
                "cours_d_eau": "Niger",
                "latitude": 16.2714,
                "longitude": -3.3936,
                "latitude_river": 16.2730,
                "longitude_river": -3.3910,
                "seuil_vigilance": 1500.0,
                "seuil_alerte": 2600.0,
                "seuil_danger": 3800.0,
                "zone_name": "Tombouctou",
            },
            {
                "nom": "Gao",
                "cours_d_eau": "Niger",
                "latitude": 16.2717,
                "longitude": -0.0447,
                "latitude_river": 16.2700,
                "longitude_river": -0.0420,
                "seuil_vigilance": 1800.0,
                "seuil_alerte": 3000.0,
                "seuil_danger": 4200.0,
                "zone_name": "Gao",
            },
            {
                "nom": "Douna",
                "cours_d_eau": "Bani",
                "latitude": 13.2100,
                "longitude": -5.9000,
                "latitude_river": 13.2120,
                "longitude_river": -5.8980,
                "seuil_vigilance": 800.0,
                "seuil_alerte": 1500.0,
                "seuil_danger": 2200.0,
                "zone_name": "Sikasso",
            },
            {
                "nom": "Kayes",
                "cours_d_eau": "Sénégal",
                "latitude": 14.4469,
                "longitude": -11.4445,
                "latitude_river": 14.4480,
                "longitude_river": -11.4420,
                "seuil_vigilance": 1100.0,
                "seuil_alerte": 2000.0,
                "seuil_danger": 2900.0,
                "zone_name": "Kayes",
            },
        ]

        created_count = 0
        updated_count = 0

        for item in stations_data:
            zone_name = item.pop("zone_name", None)
            zone = MonitoringZone.objects.filter(name__icontains=zone_name).first() if zone_name else None

            station, created = HydrologicalStation.objects.update_or_create(
                nom=item["nom"],
                defaults={
                    **item,
                    "zone": zone,
                    "is_active": True,
                }
            )
            if created:
                created_count += 1
            else:
                updated_count += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Successfully seeded hydrological stations: {created_count} created, {updated_count} updated."
            )
        )
