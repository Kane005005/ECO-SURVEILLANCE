import json
from django.test import TestCase, Client, override_settings
from django.core.cache import cache
from data_providers.gee import GEEProvider


@override_settings(CACHES={"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}})
class GEETest(TestCase):
    def setUp(self):
        self.client = Client()
        self.provider = GEEProvider()
        cache.clear()

    def tearDown(self):
        self.provider.close()
        cache.clear()

    def test_gee_health_check(self):
        """Test GEE provider health check."""
        health = self.provider.health_check()
        self.assertIn(health.status, ["ok", "degraded", "not_configured"])
        self.assertIsNotNone(health.reason)

    def test_get_leaflet_tile_url_forest(self):
        """Test generating XYZ tile URL for forest canopy layer."""
        res = self.provider.get_leaflet_tile_url(layer_type="forest")
        self.assertEqual(res["status"], "ok")
        self.assertIn("tile_url", res)
        self.assertEqual(res["layer"], "forest")
        self.assertIn("layer_name", res)

    def test_get_leaflet_tile_url_ndvi_and_ndmi(self):
        """Test generating XYZ tile URLs for NDVI and NDMI layers."""
        ndvi_res = self.provider.get_leaflet_tile_url(layer_type="ndvi")
        self.assertEqual(ndvi_res["status"], "ok")
        self.assertEqual(ndvi_res["layer"], "ndvi")

        ndmi_res = self.provider.get_leaflet_tile_url(layer_type="ndmi")
        self.assertEqual(ndmi_res["status"], "ok")
        self.assertEqual(ndmi_res["layer"], "ndmi")

    def test_tile_url_caching(self):
        """Test 12-hour Redis tile caching."""
        res1 = self.provider.get_leaflet_tile_url(layer_type="forest", start_date="2026-08-01", end_date="2026-08-20")
        self.assertFalse(res1.get("cached", False))

        res2 = self.provider.get_leaflet_tile_url(layer_type="forest", start_date="2026-08-01", end_date="2026-08-20")
        self.assertTrue(res2.get("cached", False))

    def test_get_forest_zonal_stats(self):
        """Test computing forest zonal stats (mean NDVI, NDMI, canopy cover)."""
        polygon = {
            "type": "Polygon",
            "coordinates": [[
                [-7.5, 11.2], [-7.2, 11.2], [-7.2, 11.5], [-7.5, 11.5], [-7.5, 11.2]
            ]]
        }
        stats = self.provider.get_forest_zonal_stats(polygon)
        self.assertEqual(stats["status"], "ok")
        self.assertIn("mean_ndvi", stats)
        self.assertIn("mean_ndmi", stats)
        self.assertIn("canopy_cover_pct", stats)
        self.assertIn("health_status", stats)

    def test_api_satellite_gee_tiles(self):
        """Test GET /api/satellite/gee-tiles/?layer=forest returns 200 and tile_url."""
        response = self.client.get("/api/satellite/gee-tiles/?layer=forest")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "ok")
        self.assertIn("tile_url", data)
        self.assertEqual(data["layer"], "forest")

    def test_api_forestry_zonal_stats_post(self):
        """Test POST /api/forestry/zonal-stats/ with GeoJSON payload."""
        payload = {
            "geometry": {
                "type": "Polygon",
                "coordinates": [[
                    [-7.5, 11.2], [-7.2, 11.2], [-7.2, 11.5], [-7.5, 11.5], [-7.5, 11.2]
                ]]
            }
        }
        response = self.client.post(
            "/api/forestry/zonal-stats/",
            data=json.dumps(payload),
            content_type="application/json"
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "ok")
        self.assertIn("mean_ndvi", data)
        self.assertIn("canopy_cover_pct", data)

    def test_base_methods(self):
        """Test BaseDataProvider methods search, fetch, normalize, save."""
        search_res = self.provider.search()
        self.assertIsInstance(search_res, list)

        fetch_res = self.provider.fetch(layer="forest")
        self.assertEqual(len(fetch_res), 1)

        norm_res = self.provider.normalize(fetch_res[0])
        self.assertEqual(len(norm_res), 1)

        saved = self.provider.save(norm_res)
        self.assertEqual(saved, 1)
