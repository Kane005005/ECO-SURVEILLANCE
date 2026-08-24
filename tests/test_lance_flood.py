from django.test import TestCase
import numpy as np
import io
from PIL import Image
from apps.water.models import FloodObservation
from apps.geography.models import MonitoringZone
from data_providers.lance_flood import LANCEFloodProvider


class LANCEFloodProviderTest(TestCase):
    """Tests unitaires pour le provider NASA LANCE Flood VIIRS NRT3."""

    def setUp(self):
        self.zone = MonitoringZone.objects.create(
            name="Mopti Delta", zone_type="WETLAND", latitude=14.85, longitude=-4.25, area_km2=2000
        )
        self.provider = LANCEFloodProvider(demo_mode=True)

    def test_health_check(self):
        health = self.provider.health_check()
        self.assertEqual(health.status, "ok")

    def test_search_tiles(self):
        items = self.provider.search(date="2026-08-24")
        self.assertEqual(len(items), 2)
        tiles = [i["tile"] for i in items]
        self.assertIn("h16v07", tiles)
        self.assertIn("h17v07", tiles)

    def test_raster_decoding_with_numpy(self):
        # Create a synthetic 100x100 raster with 20 pixels of class 3 (observed flood)
        arr = np.zeros((100, 100), dtype=np.uint8)
        arr[10:14, 10:15] = 3  # 20 pixels of flood
        arr[50:60, 50:60] = 2  # 100 pixels of permanent water

        img = Image.fromarray(arr)
        buf = io.BytesIO()
        img.save(buf, format="TIFF")
        raw_bytes = buf.getvalue()

        decoded = self.provider._decode_geotiff_raster(raw_bytes, "h17v07")
        self.assertEqual(decoded["flooded_pixels_count"], 20)
        expected_km2 = round(20 * self.provider.KM2_PER_PIXEL, 2)
        self.assertEqual(decoded["flooded_area_km2"], expected_km2)
        self.assertEqual(decoded["geojson"]["type"], "FeatureCollection")
        self.assertGreater(len(decoded["geojson"]["features"]), 0)

    def test_fetch_and_save_flood_observations(self):
        results = self.provider.fetch(date="2026-08-24")
        self.assertEqual(len(results), 2)
        normalized = self.provider.normalize(results)
        saved = self.provider.save(normalized)
        self.assertEqual(saved, 2)
        self.assertEqual(FloodObservation.objects.count(), 2)

        obs = FloodObservation.objects.filter(tile_name="h17v07").first()
        self.assertIsNotNone(obs)
        self.assertGreater(obs.flooded_area_km2, 0)
        self.assertEqual(obs.source, "NASA LANCE VIIRS NRT3")
