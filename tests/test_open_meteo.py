from django.test import TestCase, Client, override_settings
from django.core.cache import cache
from data_providers.open_meteo import OpenMeteoProvider


@override_settings(CACHES={"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}})
class OpenMeteoProviderTest(TestCase):
    def setUp(self):
        self.provider = OpenMeteoProvider()
        self.client = Client()
        cache.clear()

    def tearDown(self):
        self.provider.close()
        cache.clear()

    def test_decode_weather_code(self):
        """Test WMO weather code translation to French labels, emoji and icons."""
        clear = self.provider.decode_weather_code(0)
        self.assertEqual(clear["label"], "Ciel dégagé")
        self.assertEqual(clear["emoji"], "☀️")
        self.assertEqual(clear["icon"], "fa-sun")

        cloudy = self.provider.decode_weather_code(2)
        self.assertIn("Partiellement", cloudy["label"])
        self.assertEqual(cloudy["emoji"], "⛅")

        rain = self.provider.decode_weather_code(61)
        self.assertIn("Pluie", rain["label"])
        self.assertEqual(rain["emoji"], "🌧️")

        storm = self.provider.decode_weather_code(95)
        self.assertIn("Orage", storm["label"])
        self.assertEqual(storm["emoji"], "⛈️")

    def test_health_check(self):
        """Test provider health check endpoint ping."""
        health = self.provider.health_check()
        self.assertIn(health.status, ["ok", "degraded", "error"])

    def test_fetch_live_weather_structure(self):
        """Test live weather response payload structure for Bamako."""
        live = self.provider.fetch_live_weather(12.6392, -8.0029)
        self.assertIn("current", live)
        self.assertIn("temperature_c", live["current"])
        self.assertIn("condition", live["current"])
        self.assertIn("emoji", live["current"])
        self.assertIn("hourly_24h", live)

    def test_fetch_7d_forecast_structure(self):
        """Test 7-day forecast payload structure for Mopti."""
        forecast = self.provider.fetch_7d_forecast(14.4958, -4.1856)
        self.assertIn("total_precipitation_7d_mm", forecast)
        self.assertIn("days", forecast)

    def test_api_climate_live_city(self):
        """Test /api/climate/live/?city=Bamako returns 200 OK."""
        response = self.client.get("/api/climate/live/?city=Bamako")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "ok")
        self.assertIn("current", data)
        self.assertIn("temperature_c", data["current"])

    def test_api_climate_live_coordinates_and_cache(self):
        """Test /api/climate/live/?lat=...&lon=... with 20-minute caching."""
        # 1st call: fresh fetch
        res1 = self.client.get("/api/climate/live/?lat=12.8628&lon=-7.5598")
        self.assertEqual(res1.status_code, 200)
        data1 = res1.json()
        self.assertFalse(data1.get("cached", False))

        # 2nd call: served from cache
        res2 = self.client.get("/api/climate/live/?lat=12.8628&lon=-7.5598")
        self.assertEqual(res2.status_code, 200)
        data2 = res2.json()
        self.assertTrue(data2.get("cached", False))

    def test_api_climate_live_all_cities_overview(self):
        """Test /api/climate/live/ returns all 8 sentinel cities of Mali."""
        response = self.client.get("/api/climate/live/")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "ok")
        self.assertEqual(data["count"], 8)
        self.assertEqual(len(data["cities"]), 8)
        city_names = [c["city"] for c in data["cities"]]
        self.assertIn("Bamako", city_names)
        self.assertIn("Mopti", city_names)
        self.assertIn("Gao", city_names)
