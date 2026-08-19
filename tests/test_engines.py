"""
Tests for core engines: Anomaly, Risk, IEZ.
"""
from django.test import TestCase
from decimal import Decimal
from core.services.anomaly import AnomalyEngine, ZoneAnomalyScanner
from core.services.risk import RiskEngine, RiskResult
from core.services.iez import IEZEngine


class AnomalyEngineTest(TestCase):
    def setUp(self):
        self.engine = AnomalyEngine()

    def test_no_anomaly_normal_values(self):
        result = self.engine.detect("NDVI", Decimal("0.6"), Decimal("0.55"), Decimal("0.1"))
        self.assertFalse(result.detected)
        self.assertEqual(result.severity, "NONE")

    def test_low_anomaly(self):
        result = self.engine.detect("NDVI", Decimal("0.35"), Decimal("0.55"), Decimal("0.1"))
        self.assertTrue(result.detected)
        self.assertEqual(result.severity, "LOW")  # z = -2.0 (1.5 ≤ |z| < 2.5)

    def test_high_anomaly(self):
        result = self.engine.detect("TEMPERATURE", Decimal("55"), Decimal("35"), Decimal("5"))
        self.assertTrue(result.detected)
        self.assertEqual(result.severity, "HIGH")  # z = 4.0

    def test_critical_anomaly(self):
        result = self.engine.detect("SO2", Decimal("10"), Decimal("0.2"), Decimal("0.1"))
        self.assertTrue(result.detected)
        self.assertEqual(result.severity, "CRITICAL")  # z = 98

    def test_zero_std_dev(self):
        result = self.engine.detect("test", Decimal("5"), Decimal("5"), Decimal("0"))
        self.assertFalse(result.detected)

    def test_directional_above_only(self):
        # Temperature high: should detect
        result = self.engine.detect_directional("temp", Decimal("45"), Decimal("30"), Decimal("5"), "above")
        self.assertTrue(result.detected)
        # Temperature low: should NOT detect with direction="above"
        result = self.engine.detect_directional("temp", Decimal("15"), Decimal("30"), Decimal("5"), "above")
        self.assertFalse(result.detected)

    def test_directional_below_only(self):
        # NDVI low: should detect with direction="below"
        result = self.engine.detect_directional("NDVI", Decimal("0.2"), Decimal("0.6"), Decimal("0.1"), "below")
        self.assertTrue(result.detected)
        # NDVI high: should NOT detect with direction="below"
        result = self.engine.detect_directional("NDVI", Decimal("0.8"), Decimal("0.6"), Decimal("0.1"), "below")
        self.assertFalse(result.detected)

    def test_multi_signal(self):
        signals = [
            {"metric": "fire_detections", "current": 80, "baseline": 20, "std_dev": 10},
            {"metric": "temperature", "current": 42, "baseline": 30, "std_dev": 5},
        ]
        result = self.engine.detect_multi_signal(signals)
        self.assertTrue(result["detected"])
        self.assertEqual(result["detected_count"], 2)

    def test_compute_baseline_stats(self):
        values = [1.0, 2.0, 3.0, 4.0, 5.0]
        mean, std = self.engine.compute_baseline_stats(values)
        self.assertAlmostEqual(mean, 3.0)
        self.assertGreater(std, 0)


class RiskEngineTest(TestCase):
    def setUp(self):
        self.engine = RiskEngine()

    def test_compute_wildfire_risk(self):
        result = self.engine.compute("WILDFIRE", {
            "fire_detections": 90,
            "temperature": 80,
            "wind_speed": 60,
            "humidity": 70,
            "precipitation": 40,
            "vegetation_dryness": 80,
        })
        self.assertIsInstance(result, RiskResult)
        self.assertGreater(result.risk_score, 50)
        self.assertEqual(result.level, "ORANGE")
        self.assertEqual(result.severity, "HIGH")

    def test_compute_low_risk(self):
        result = self.engine.compute("WILDFIRE", {
            "fire_detections": 10,
            "temperature": 30,
            "wind_speed": 20,
            "humidity": 70,
            "precipitation": 80,
            "vegetation_dryness": 20,
        })
        self.assertLess(result.risk_score, 40)
        self.assertIn(result.level, ["GREEN", "YELLOW"])

    def test_unknown_risk_type(self):
        result = self.engine.compute("UNKNOWN", {})
        self.assertEqual(result.risk_score, 0)

    def test_result_to_dict(self):
        result = self.engine.compute("WILDFIRE", {"fire_detections": 50})
        d = result.to_dict()
        self.assertIn("risk_score", d)
        self.assertIn("factors", d)
        self.assertIsInstance(d["factors"], list)

    def test_risk_profiles_defined(self):
        expected = ["WILDFIRE", "DROUGHT", "VEGETATION_DEGRADATION", "WATER_POLLUTION", "WATER_STRESS", "HEAT", "ATMOSPHERIC_ANOMALY"]
        for rt in expected:
            self.assertIn(rt, self.engine.RISK_PROFILES)


class IEZEngineTest(TestCase):
    def setUp(self):
        self.engine = IEZEngine()

    def test_perfect_score(self):
        components = {k: Decimal("100") for k in ["vegetation", "water", "climate", "fire", "atmosphere", "human_pressure", "vulnerability"]}
        result = self.engine.compute(components)
        self.assertEqual(result["iez"], "100.00")
        self.assertEqual(result["level"], "BON")

    def test_zero_score(self):
        components = {k: Decimal("0") for k in ["vegetation", "water", "climate", "fire", "atmosphere", "human_pressure", "vulnerability"]}
        result = self.engine.compute(components)
        self.assertEqual(result["iez"], "0.00")
        self.assertEqual(result["level"], "CRITIQUE")

    def test_mixed_scores(self):
        components = {
            "vegetation": Decimal("80"),
            "water": Decimal("60"),
            "climate": Decimal("70"),
            "fire": Decimal("90"),
            "atmosphere": Decimal("75"),
            "human_pressure": Decimal("50"),
            "vulnerability": Decimal("65"),
        }
        result = self.engine.compute(components)
        iez = float(result["iez"])
        self.assertGreater(iez, 50)
        self.assertLess(iez, 100)
        self.assertIn(result["level"], ["BON", "VIGILANCE", "DÉGRADÉ"])

    def test_custom_weights(self):
        components = {"vegetation": Decimal("100"), "water": Decimal("0")}
        weights = {"vegetation": Decimal("1.0"), "water": Decimal("0.0")}
        result = self.engine.compute(components, weights)
        self.assertEqual(result["iez"], "100.00")

    def test_level_transitions(self):
        # 85+ = BON
        r = self.engine.compute({"v": Decimal("85")}, {"v": Decimal("1.0")})
        self.assertEqual(r["level"], "BON")

        # 65-84 = VIGILANCE
        r = self.engine.compute({"v": Decimal("70")}, {"v": Decimal("1.0")})
        self.assertEqual(r["level"], "VIGILANCE")

        # 40-64 = DÉGRADÉ
        r = self.engine.compute({"v": Decimal("50")}, {"v": Decimal("1.0")})
        self.assertEqual(r["level"], "DÉGRADÉ")

        # <40 = CRITIQUE
        r = self.engine.compute({"v": Decimal("30")}, {"v": Decimal("1.0")})
        self.assertEqual(r["level"], "CRITIQUE")
