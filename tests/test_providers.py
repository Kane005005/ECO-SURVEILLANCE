"""
Tests for data providers — unit tests with mocks (no external API calls).
"""
from django.test import TestCase
from unittest.mock import patch, MagicMock
from datetime import datetime
from django.utils import timezone
from data_providers.base import BaseDataProvider, DataSourceResult, ProviderHealth
from data_providers.firms import FIRMSProvider
from data_providers.nasa_power import NASAPowerProvider
from data_providers.sentinel2 import Sentinel2Provider
from data_providers.sentinel5p import Sentinel5PProvider
from data_providers.landsat import LandsatProvider
from data_providers.openaq import OpenAQProvider


class BaseProviderTest(TestCase):
    def test_datasource_result(self):
        result = DataSourceResult(
            source="test", data={"key": "value"},
            fetched_at=timezone.now(), is_simulated=False
        )
        self.assertEqual(result.source, "test")
        self.assertFalse(result.is_simulated)

    def test_provider_health(self):
        h = ProviderHealth(status="ok")
        self.assertEqual(h.status, "ok")
        h2 = ProviderHealth(status="error", reason="missing key")
        self.assertEqual(h2.reason, "missing key")


class FIRMSProviderTest(TestCase):
    def test_health_check_no_key(self):
        provider = FIRMSProvider(map_key=None)
        health = provider.health_check()
        self.assertEqual(health.status, "not_configured")

    def test_health_check_with_key(self):
        provider = FIRMSProvider(map_key="test-key-123")
        health = provider.health_check()
        self.assertEqual(health.status, "ok")

    def test_normalize_firms_data(self):
        provider = FIRMSProvider(map_key="test")
        raw = {
            "latitude": 14.5,
            "longitude": -4.2,
            "acq_date": "2024-01-15",
            "acq_time": "1430",
            "satellite": "VIIRS",
            "confidence": "high",
            "bright_ti4": 350.5,
            "frp": 45.2,
            "scan": 1.0,
            "track": 1.0,
            "daynight": "D",
        }
        normalized = provider.normalize(raw)
        self.assertEqual(len(normalized), 1)
        record = normalized[0]
        self.assertEqual(record["latitude"], 14.5)
        self.assertEqual(record["longitude"], -4.2)
        self.assertEqual(record["satellite"], "VIIRS")
        self.assertEqual(record["confidence"], "high")
        self.assertAlmostEqual(record["brightness"], 350.5)
        self.assertAlmostEqual(record["frp"], 45.2)

    def test_normalize_empty_data(self):
        provider = FIRMSProvider(map_key="test")
        result = provider.normalize({"no_valid_fields": True})
        self.assertIsInstance(result, list)

    @patch("requests.Session.get")
    def test_search_mock(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "data": [[14.5, -4.2, "2024-01-15", "1430", "VIIRS", "high", 350.5, 45.2, 1.0, 1.0, "D"]]
        }
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        provider = FIRMSProvider(map_key="test-key")
        results = provider.search(
            geometry={"type": "Point", "coordinates": [-4.2, 14.5]},
            date_range=("2024-01-15", "2024-01-16")
        )
        self.assertIsNotNone(results)


class NASAPowerProviderTest(TestCase):
    def test_health_check_open_access(self):
        provider = NASAPowerProvider()
        with patch.object(provider.session, 'get') as mock_get:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_get.return_value = mock_resp
            health = provider.health_check()
            self.assertEqual(health.status, "ok")

    def test_normalize_power_data(self):
        provider = NASAPowerProvider()
        raw = {
            "lat": 12.64,
            "lon": -8.0,
            "data": {
                "properties": {
                    "parameter": {
                        "T2M": {"20240101": 32.5, "20240102": 33.1},
                        "RH2M": {"20240101": 45.0, "20240102": 48.2},
                    }
                }
            }
        }
        normalized = provider.normalize(raw)
        self.assertGreater(len(normalized), 0)
        temp_records = [r for r in normalized if r["variable"] == "TEMPERATURE"]
        self.assertEqual(len(temp_records), 2)
        self.assertAlmostEqual(temp_records[0]["value"], 32.5)

    def test_variable_mapping(self):
        self.assertIn("T2M", NASAPowerProvider.VARIABLE_MAP)
        self.assertEqual(NASAPowerProvider.VARIABLE_MAP["T2M"][0], "TEMPERATURE")
        self.assertIn("RH2M", NASAPowerProvider.VARIABLE_MAP)


class Sentinel2ProviderTest(TestCase):
    def test_health_check_no_credentials(self):
        provider = Sentinel2Provider(client_id="", client_secret="")
        health = provider.health_check()
        self.assertEqual(health.status, "not_configured")

    def test_indices_formulas(self):
        self.assertIn("NDVI", Sentinel2Provider.INDICES)
        self.assertIn("NDWI", Sentinel2Provider.INDICES)
        self.assertIn("NBR", Sentinel2Provider.INDICES)
        self.assertIn("NDMI", Sentinel2Provider.INDICES)
        self.assertIn("B04", Sentinel2Provider.INDICES["NDVI"]["bands"])
        self.assertIn("B08", Sentinel2Provider.INDICES["NDVI"]["bands"])

    def test_extract_center_point(self):
        geom = {"type": "Point", "coordinates": [-8.0, 12.64]}
        lat, lng = Sentinel2Provider._extract_center(geom)
        self.assertAlmostEqual(lat, 12.64)
        self.assertAlmostEqual(lng, -8.0)

    def test_extract_center_polygon(self):
        geom = {
            "type": "Polygon",
            "coordinates": [[[-8, 12], [-7, 12], [-7, 13], [-8, 13], [-8, 12]]]
        }
        lat, lng = Sentinel2Provider._extract_center(geom)
        self.assertAlmostEqual(lat, 12.4)
        self.assertAlmostEqual(lng, -7.6)

    def test_normalize_demo_mode(self):
        provider = Sentinel2Provider(client_id="test", client_secret="test", demo_mode=True)
        raw = {
            "product_id": "S2A_MSIL2A_20240101",
            "properties": {"datetime": "2024-01-01T00:00:00Z"},
            "bands": {},
            "geometry": {"type": "Point", "coordinates": [-8.0, 12.64]},
        }
        normalized = provider.normalize(raw)
        self.assertGreater(len(normalized), 0)
        indices = [r["index_name"] for r in normalized]
        self.assertIn("NDVI", indices)
        self.assertIn("NDWI", indices)


class Sentinel5PProviderTest(TestCase):
    def test_health_check_no_credentials(self):
        provider = Sentinel5PProvider(client_id="", client_secret="")
        health = provider.health_check()
        self.assertEqual(health.status, "not_configured")

    def test_products_defined(self):
        self.assertIn("SO2", Sentinel5PProvider.PRODUCTS)
        self.assertIn("O3", Sentinel5PProvider.PRODUCTS)
        self.assertIn("AER_AI", Sentinel5PProvider.PRODUCTS)

    def test_variable_map(self):
        self.assertIn("SO2", Sentinel5PProvider.VARIABLE_MAP)
        self.assertIn("O3", Sentinel5PProvider.VARIABLE_MAP)
        self.assertIn("AER_AI", Sentinel5PProvider.VARIABLE_MAP)


class LandsatProviderTest(TestCase):
    @patch("requests.Session.get")
    def test_health_check_ok(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_get.return_value = mock_resp
        provider = LandsatProvider()
        health = provider.health_check()
        self.assertEqual(health.status, "ok")

    @patch("requests.Session.post")
    def test_search_returns_results(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = {"features": [{"id": "LC08_TEST", "geometry": None, "properties": {"eo:cloud_cover": 5, "datetime": "2025-07-01"}, "assets": {}, "bbox": None}]}
        mock_post.return_value = mock_resp
        provider = LandsatProvider()
        results = provider.search(aoi={"west": -9, "south": 12, "east": -7, "north": 14})
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["id"], "LC08_TEST")

    def test_normalize_empty(self):
        provider = LandsatProvider()
        normalized = provider.normalize({})
        self.assertEqual(normalized, [])

    @patch("requests.Session.get")
    def test_health_check_with_mock(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_get.return_value = mock_resp
        provider = LandsatProvider()
        health = provider.health_check()
        self.assertEqual(health.status, "ok")


class OpenAQProviderTest(TestCase):
    def test_health_check_no_key(self):
        provider = OpenAQProvider(api_key="")
        health = provider.health_check()
        self.assertEqual(health.status, "not_configured")

    @patch("requests.Session.get")
    def test_health_check_with_key(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = {"meta": {"found": 10}}
        mock_resp.elapsed.total_seconds.return_value = 0.1
        mock_get.return_value = mock_resp

        provider = OpenAQProvider(api_key="test-key")
        health = provider.health_check()
        self.assertEqual(health.status, "ok")

    def test_search_no_key(self):
        provider = OpenAQProvider(api_key="")
        results = provider.search(latitude=12.64, longitude=-8.0)
        self.assertEqual(results, [])

    def test_parameter_map(self):
        self.assertIn("pm25", OpenAQProvider.PARAMETER_MAP)
        self.assertIn("no2", OpenAQProvider.PARAMETER_MAP)
        self.assertIn("o3", OpenAQProvider.PARAMETER_MAP)

    def test_normalize_empty(self):
        provider = OpenAQProvider(api_key="test")
        normalized = provider.normalize({})
        self.assertEqual(normalized, [])

    def test_normalize_measurements(self):
        provider = OpenAQProvider(api_key="test")
        raw = {
            "location_id": 123,
            "location_name": "Bamako Station",
            "coordinates": {"latitude": 12.64, "longitude": -8.0},
            "measurements": [
                {
                    "parameter": {"name": "pm25", "units": "µg/m³"},
                    "value": 45.2,
                    "date": {"utc": "2024-01-15T14:30:00Z"},
                }
            ],
        }
        normalized = provider.normalize(raw)
        self.assertEqual(len(normalized), 1)
        self.assertEqual(normalized[0]["variable"], "PM25")
        self.assertEqual(normalized[0]["value"], 45.2)
        self.assertEqual(normalized[0]["location_name"], "Bamako Station")


class AIProviderTest(TestCase):
    def test_openai_compat_no_key(self):
        from ai.openai_compat import OpenAICompatProvider
        provider = OpenAICompatProvider(api_key="")
        health = provider.health_check()
        self.assertEqual(health["status"], "degraded")

    def test_openai_compat_chat_no_key(self):
        from ai.openai_compat import OpenAICompatProvider
        provider = OpenAICompatProvider(api_key="")
        result = provider._chat("system", "user")
        self.assertEqual(result, "")

    @patch("ai.groq.GroqProvider.__init__", lambda self, **kw: None)
    def test_groq_no_key(self):
        from ai.groq import GroqProvider
        provider = GroqProvider()
        provider.api_key = ""
        health = provider.health_check()
        self.assertEqual(health["status"], "degraded")
