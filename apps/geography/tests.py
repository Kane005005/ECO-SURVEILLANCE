from django.test import TestCase, Client
from django.core.management import call_command
from django.urls import reverse
from .models import Country, Region, RegionalDirectorate, MonitoringZone

class RegionalModelsAndSeedTestCase(TestCase):
    def setUp(self):
        self.client = Client()

    def test_seed_command_creates_20_entities_and_directorates(self):
        """Vérifie que la commande de seed crée bien les 19 régions + Bamako et les directions régionales."""
        call_command("seed_mali_regions_and_directorates")

        # 19 Régions + 1 District = 20
        self.assertEqual(Region.objects.count(), 20)

        # Vérifier la présence du District de Bamako et des 19 régions
        bko = Region.objects.get(code="BKO")
        self.assertEqual(bko.name, "District de Bamako")
        self.assertEqual(bko.region_number, 0)
        self.assertAlmostEqual(bko.latitude, 12.6392, places=3)
        self.assertAlmostEqual(bko.longitude, -8.0029, places=3)

        segou = Region.objects.get(code="SEG")
        self.assertEqual(segou.name, "Ségou")
        self.assertEqual(segou.region_number, 4)
        self.assertEqual(segou.capital, "Ségou")

        mopti = Region.objects.get(code="MOP")
        self.assertEqual(mopti.name, "Mopti")
        self.assertEqual(mopti.region_number, 5)

        bandiagara = Region.objects.get(code="BAN")
        self.assertEqual(bandiagara.name, "Bandiagara")
        self.assertEqual(bandiagara.region_number, 19)

        # Vérifier que toutes les DRPC ont le numéro vert 122
        drpcs = RegionalDirectorate.objects.filter(directorate_type="DRPC")
        self.assertGreaterEqual(drpcs.count(), 20)
        for drpc in drpcs:
            self.assertEqual(drpc.emergency_number, "122")

        # Vérifier les directions régionales spécialisées pour Ségou
        segou_dirs = RegionalDirectorate.objects.filter(region=segou)
        types = set(segou_dirs.values_list("directorate_type", flat=True))
        self.assertTrue({"DRPC", "DRH", "DREF", "DRACPN", "DRA"}.issubset(types))

        # Vérifier l'icône et la couleur de badge
        drpc_segou = segou_dirs.get(directorate_type="DRPC")
        self.assertEqual(drpc_segou.icon_class, "fas fa-shield-halved")
        self.assertEqual(drpc_segou.badge_color, "#DC2626")

        drh_segou = segou_dirs.get(directorate_type="DRH")
        self.assertEqual(drh_segou.icon_class, "fas fa-droplet")
        self.assertEqual(drh_segou.badge_color, "#0284C7")

    def test_zone_competent_directorates_resolution(self):
        """Vérifie la résolution automatique des directions régionales pour une zone d'alerte."""
        country = Country.objects.create(code="MLI", name="Mali")
        region = Region.objects.create(
            country=country,
            name="Ségou",
            code="SEG",
            region_number=4,
            capital="Ségou",
            latitude=13.4317,
            longitude=-6.2157
        )
        drpc = RegionalDirectorate.objects.create(
            region=region,
            directorate_type="DRPC",
            name="DRPC Ségou",
            latitude=13.435,
            longitude=-6.22,
            phone_primary="+223 21 32 18 77",
            emergency_number="122"
        )
        drh = RegionalDirectorate.objects.create(
            region=region,
            directorate_type="DRH",
            name="DRH Ségou",
            latitude=13.438,
            longitude=-6.212,
            phone_primary="+223 21 32 04 15",
            emergency_number="122"
        )

        zone = MonitoringZone.objects.create(
            name="Plaines Agricoles de Markala",
            zone_type="AGRICULTURAL",
            region=region,
            latitude=13.7,
            longitude=-6.06
        )

        # Résolution automatique via zone.region.directorates
        competent = zone.get_competent_directorates()
        self.assertEqual(competent.count(), 2)
        self.assertIn(drpc, competent)
        self.assertIn(drh, competent)

class GeographyAPITests(TestCase):
    def setUp(self):
        self.client = Client()
        call_command("seed_mali_regions_and_directorates")
        bko = Region.objects.get(code="BKO")
        self.zone = MonitoringZone.objects.create(
            name="Bamako Centre",
            zone_type="URBAN",
            region=bko,
            latitude=12.6392,
            longitude=-8.0029,
            status="MONITORING"
        )
        self.zone.competent_directorates.set(bko.directorates.all())

    def test_regions_api_endpoint(self):
        """Teste GET /api/geography/regions/"""
        response = self.client.get("/api/geography/regions/")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["count"], 20)
        self.assertEqual(len(data["regions"]), 20)

        # Vérifie la présence des coordonnées et chefs-lieux
        first = data["regions"][0]
        self.assertIn("capital", first)
        self.assertIn("latitude", first)
        self.assertIn("longitude", first)
        self.assertIn("directorates_count", first)

        # Test recherche par mot-clé
        res_search = self.client.get("/api/geography/regions/?search=mopti")
        self.assertEqual(res_search.status_code, 200)
        search_data = res_search.json()
        self.assertEqual(search_data["count"], 1)
        self.assertEqual(search_data["regions"][0]["name"], "Mopti")

    def test_directorates_api_endpoint_and_filters(self):
        """Teste GET /api/geography/directorates/?region=...&type=..."""
        # 1. Tous les directorates
        response = self.client.get("/api/geography/directorates/")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertGreaterEqual(data["count"], 40)

        # 2. Filtre par code de région et par type DRPC
        res_filtered = self.client.get("/api/geography/directorates/?region=SEG&type=DRPC")
        self.assertEqual(res_filtered.status_code, 200)
        fdata = res_filtered.json()
        self.assertEqual(fdata["count"], 1)
        dir_obj = fdata["directorates"][0]
        self.assertEqual(dir_obj["directorate_type"], "DRPC")
        self.assertEqual(dir_obj["emergency_number"], "122")
        self.assertEqual(dir_obj["region"]["code"], "SEG")
        self.assertIn("+223 21 32 18 77", dir_obj["phone_primary"])

        # 3. Filtre par ID de région
        seg_id = Region.objects.get(code="SEG").id
        res_id = self.client.get(f"/api/geography/directorates/?region={seg_id}")
        self.assertEqual(res_id.status_code, 200)
        self.assertEqual(res_id.json()["count"], 5)

    def test_directorates_by_zone_endpoint(self):
        """Teste GET /api/geography/directorates/by-zone/<zone_id>/"""
        zone = MonitoringZone.objects.first()
        self.assertIsNotNone(zone)

        response = self.client.get(f"/api/geography/directorates/by-zone/{zone.id}/")
        self.assertEqual(response.status_code, 200)
        data = response.json()

        self.assertIn("zone", data)
        self.assertEqual(data["zone"]["id"], zone.id)
        self.assertIn("emergency_contacts", data)
        self.assertEqual(data["emergency_contacts"]["national_emergency"], "122")
        self.assertIn("sms_dispatch_template", data)
        self.assertIn("122", data["sms_dispatch_template"])
        self.assertIn("directorates", data)
        self.assertGreaterEqual(len(data["directorates"]), 1)

    def test_directorates_by_zone_not_found(self):
        """Teste 404 sur zone inexistante."""
        response = self.client.get("/api/geography/directorates/by-zone/99999/")
        self.assertEqual(response.status_code, 404)

    def test_map_api_includes_directorates_and_admin_regions(self):
        """Vérifie que l'endpoint central /api/map/ intègre les calques demandés."""
        response = self.client.get("/api/map/")
        self.assertEqual(response.status_code, 200)
        d = response.json()
        self.assertIn("directorates", d)
        self.assertIn("admin_regions", d)
        self.assertEqual(len(d["admin_regions"]), 20)
        self.assertGreaterEqual(len(d["directorates"]), 40)
