import json
from django.test import TestCase, Client, override_settings
from django.core.cache import cache
from apps.reports.models import FieldReport


@override_settings(CACHES={"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}})
class FieldReportTest(TestCase):
    def setUp(self):
        self.client = Client()
        cache.clear()
        self.report = FieldReport.objects.create(
            latitude=14.4958,
            longitude=-4.1856,
            report_type="FLOOD",
            severity="HIGH",
            title="Crue test Mopti",
            description="Test description crue",
            author_name="Observateur Test",
            author_phone="+223 70 00 00 00",
            is_verified=True
        )

    def tearDown(self):
        cache.clear()

    def test_field_report_model(self):
        """Test FieldReport model creation and methods."""
        self.assertIn("Crue test Mopti", str(self.report))
        geojson = self.report.to_geojson_feature()
        self.assertEqual(geojson["type"], "Feature")
        self.assertEqual(geojson["geometry"]["coordinates"], [-4.1856, 14.4958])
        self.assertEqual(geojson["properties"]["report_type"], "FLOOD")
        self.assertEqual(geojson["properties"]["severity"], "HIGH")
        self.assertTrue(geojson["properties"]["is_verified"])

    def test_api_report_create_success(self):
        """Test POST /api/reports/create/ with valid payload returns 201 Created."""
        payload = {
            "latitude": 12.6392,
            "longitude": -8.0029,
            "report_type": "WILDFIRE",
            "severity": "CRITICAL",
            "title": "Feu de brousse Kati",
            "description": "Foyer actif observé près de la colline",
            "author_name": "Agent Eaux & Forêts",
            "author_phone": "+223 71 22 33 44"
        }
        response = self.client.post(
            "/api/reports/create/",
            data=json.dumps(payload),
            content_type="application/json"
        )
        self.assertEqual(response.status_code, 201)
        data = response.json()
        self.assertEqual(data["status"], "ok")
        self.assertIn("report", data)
        self.assertEqual(data["report"]["title"], "Feu de brousse Kati")
        self.assertEqual(data["report"]["report_type"], "WILDFIRE")
        self.assertEqual(data["report"]["severity"], "CRITICAL")

        # Verify in DB
        created_in_db = FieldReport.objects.filter(title="Feu de brousse Kati").first()
        self.assertIsNotNone(created_in_db)
        self.assertEqual(created_in_db.latitude, 12.6392)

    def test_api_report_create_validation_errors(self):
        """Test POST /api/reports/create/ returns 400 when required fields or coordinates are missing."""
        # Missing coordinates
        res1 = self.client.post(
            "/api/reports/create/",
            data=json.dumps({"title": "Test sans coord"}),
            content_type="application/json"
        )
        self.assertEqual(res1.status_code, 400)

        # Invalid coordinates (out of range)
        res2 = self.client.post(
            "/api/reports/create/",
            data=json.dumps({"latitude": 150.0, "longitude": -8.0, "title": "Test hors limites"}),
            content_type="application/json"
        )
        self.assertEqual(res2.status_code, 400)

        # Missing title
        res3 = self.client.post(
            "/api/reports/create/",
            data=json.dumps({"latitude": 12.0, "longitude": -8.0, "title": ""}),
            content_type="application/json"
        )
        self.assertEqual(res3.status_code, 400)

    def test_api_report_list_geojson(self):
        """Test GET /api/reports/list/ returns GeoJSON FeatureCollection."""
        response = self.client.get("/api/reports/list/")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["type"], "FeatureCollection")
        self.assertGreaterEqual(data["count"], 1)
        self.assertIsInstance(data["features"], list)
        
        feature = data["features"][0]
        self.assertEqual(feature["type"], "Feature")
        self.assertIn("geometry", feature)
        self.assertIn("properties", feature)

    def test_api_map_includes_reports(self):
        """Test GET /api/map/ includes reports layer in response."""
        response = self.client.get("/api/map/")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("reports", data)
        self.assertIsInstance(data["reports"], list)
        self.assertGreaterEqual(len(data["reports"]), 1)
