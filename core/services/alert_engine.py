"""
Alert Engine.
Automatically generates alerts when thresholds or signal combinations are exceeded.
Produces explainable alerts with source, zone, severity, and recommended actions.
"""
import logging
from typing import Dict, Any, List, Optional
from datetime import timedelta
from django.utils import timezone

logger = logging.getLogger("apps.alerts")


class AlertRule:
    """Defines a condition that triggers an alert."""

    def __init__(self, name: str, alert_type: str, severity: str, description: str, check_fn=None):
        self.name = name
        self.alert_type = alert_type  # WILDFIRE, DROUGHT, etc.
        self.severity = severity
        self.description = description
        self.check_fn = check_fn


class AlertEngine:
    """
    Evaluates all alert rules for zones and generates alerts.
    Rules are based on real data signals and thresholds.
    """

    def __init__(self):
        self.rules = self._build_rules()

    def _build_rules(self) -> List[AlertRule]:
        """Define all alert rules."""
        return [
            AlertRule(
                name="HIGH_FIRE_RISK",
                alert_type="WILDFIRE",
                severity="CRITICAL",
                description="Risque incendie élevé: feux actifs + température haute + faible humidité + végétation sèche",
            ),
            AlertRule(
                name="ACTIVE_FIRES",
                alert_type="WILDFIRE",
                severity="HIGH",
                description="Feux actifs détectés dans la zone",
            ),
            AlertRule(
                name="DROUGHT_WARNING",
                alert_type="DROUGHT",
                severity="HIGH",
                description="Déficit pluviométrique important sur 30 jours",
            ),
            AlertRule(
                name="EXTREME_HEAT",
                alert_type="HEAT",
                severity="CRITICAL",
                description="Température extrême détectée (>45°C)",
            ),
            AlertRule(
                name="VEGETATION_DECLINE",
                alert_type="VEGETATION_DEGRADATION",
                severity="MEDIUM",
                description="Déclin significatif du NDVI",
            ),
            AlertRule(
                name="WATER_POLLUTION",
                alert_type="WATER_POLLUTION",
                severity="HIGH",
                description="Anomalie de qualité de l'eau détectée",
            ),
            AlertRule(
                name="ATMOSPHERIC_POLLUTION",
                alert_type="ATMOSPHERIC_ANOMALY",
                severity="MEDIUM",
                description="Niveau élevé de polluants atmosphériques",
            ),
            AlertRule(
                name="FLOOD_WARNING",
                alert_type="FLOOD",
                severity="HIGH",
                description="Débit fluvial élevé ou crue observée par satellite",
            ),
        ]

    def evaluate_zone(self, zone) -> List[Dict[str, Any]]:
        """Evaluate all rules for a zone. Returns list of triggered alerts."""
        triggered = []

        # Rule: HIGH_FIRE_RISK
        fire_data = self._check_fire_risk(zone)
        if fire_data["triggered"]:
            triggered.append(self._make_alert(
                zone=zone, rule_name="HIGH_FIRE_RISK",
                title=f"Risque incendie élevé — {zone.name}",
                description=fire_data["description"],
                severity="CRITICAL", source="AlertEngine",
                metadata=fire_data,
            ))

        # Rule: ACTIVE_FIRES
        fire_count = self._count_recent_fires(zone, days=3)
        if fire_count >= 3:
            triggered.append(self._make_alert(
                zone=zone, rule_name="ACTIVE_FIRES",
                title=f"Feux actifs — {zone.name}",
                description=f"{fire_count} feux détectés dans les 3 derniers jours",
                severity="HIGH" if fire_count >= 5 else "MEDIUM",
                source="NASA FIRMS",
                metadata={"fire_count_3d": fire_count},
            ))

        # Rule: DROUGHT_WARNING
        precip_deficit = self._check_precipitation_deficit(zone)
        if precip_deficit["triggered"]:
            triggered.append(self._make_alert(
                zone=zone, rule_name="DROUGHT_WARNING",
                title=f"Alerte sécheresse — {zone.name}",
                description=precip_deficit["description"],
                severity="HIGH",
                source="NASA POWER / CHIRPS",
                metadata=precip_deficit,
            ))

        # Rule: EXTREME_HEAT
        heat_data = self._check_extreme_heat(zone)
        if heat_data["triggered"]:
            triggered.append(self._make_alert(
                zone=zone, rule_name="EXTREME_HEAT",
                title=f"Canicule — {zone.name}",
                description=heat_data["description"],
                severity="CRITICAL",
                source="NASA POWER",
                metadata=heat_data,
            ))

        # Rule: VEGETATION_DECLINE
        veg_data = self._check_vegetation_decline(zone)
        if veg_data["triggered"]:
            triggered.append(self._make_alert(
                zone=zone, rule_name="VEGETATION_DECLINE",
                title=f"Dégradation végétation — {zone.name}",
                description=veg_data["description"],
                severity="MEDIUM",
                source="Sentinel-2",
                metadata=veg_data,
            ))

        # Rule: WATER_POLLUTION
        water_data = self._check_water_pollution(zone)
        if water_data["triggered"]:
            triggered.append(self._make_alert(
                zone=zone, rule_name="WATER_POLLUTION",
                title=f"Pollution eau — {zone.name}",
                description=water_data["description"],
                severity="HIGH",
                source="Capteurs",
                metadata=water_data,
            ))

        # Rule: FLOOD_WARNING
        flood_data = self._check_flood_warning(zone)
        if flood_data["triggered"]:
            triggered.append(self._make_alert(
                zone=zone, rule_name="FLOOD_WARNING",
                title=f"Vigilance crue — {zone.name}",
                description=flood_data["description"],
                severity=flood_data.get("severity", "HIGH"),
                source="GloFAS / NASA LANCE Flood",
                metadata=flood_data,
            ))

        return triggered

    def evaluate_all_zones(self) -> List[Dict[str, Any]]:
        """Evaluate rules for all zones and save triggered alerts."""
        from apps.geography.models import MonitoringZone
        from apps.alerts.models import Alert
        from apps.users.models import User

        zones = MonitoringZone.objects.all()
        admin_user = User.objects.filter(is_superuser=True).first()
        all_alerts = []

        for zone in zones:
            triggered = self.evaluate_zone(zone)
            for alert_data in triggered:
                # Dedup: don't create same alert type for same zone in last 24h
                existing = Alert.objects.filter(
                    incident__zone=zone,
                    incident__title__contains=alert_data.get("rule_name", ""),
                    created_at__gte=timezone.now() - timedelta(hours=24),
                ).exists()
                if existing:
                    continue

                # Create Incident + Alert
                from apps.incidents.models import Incident
                incident = Incident.objects.create(
                    title=alert_data["title"],
                    incident_type=alert_data.get("alert_type", "GENERAL"),
                    description=alert_data["description"],
                    zone=zone,
                    latitude=zone.latitude,
                    longitude=zone.longitude,
                    severity=alert_data["severity"],
                    risk_score=alert_data.get("risk_score", 50),
                    source=alert_data.get("source", "AlertEngine"),
                    detected_at=timezone.now(),
                    status="NEW",
                    is_simulated=False,
                    metadata=alert_data.get("metadata", {}),
                )

                if admin_user:
                    Alert.objects.create(
                        incident=incident,
                        recipient=admin_user,
                        channel="WEB",
                        severity=alert_data["severity"],
                        message=alert_data["description"],
                        sent_at=timezone.now(),
                        status="SENT",
                        is_simulated=False,
                    )

                all_alerts.append(alert_data)
                logger.info("Alert created: %s for zone %s", alert_data["title"], zone.name)

        return all_alerts

    def _check_fire_risk(self, zone) -> Dict[str, Any]:
        """Check multi-signal fire risk."""
        from apps.fires.models import FireDetection
        from apps.climate.models import ClimateObservation
        from apps.vegetation.models import VegetationObservation

        now = timezone.now()
        signals = []

        fire_count = FireDetection.objects.filter(
            zone=zone, detected_at__gte=now - timedelta(days=7)
        ).count()
        signals.append(("feux_7j", fire_count, fire_count >= 2))

        temp_vals = list(ClimateObservation.objects.filter(
            zone=zone, variable="TEMPERATURE",
            observed_at__gte=now - timedelta(days=3)
        ).values_list("value", flat=True))
        avg_temp = sum(temp_vals) / len(temp_vals) if temp_vals else 30
        signals.append(("température", avg_temp, avg_temp > 40))

        hum_vals = list(ClimateObservation.objects.filter(
            zone=zone, variable="HUMIDITY",
            observed_at__gte=now - timedelta(days=3)
        ).values_list("value", flat=True))
        avg_hum = sum(hum_vals) / len(hum_vals) if hum_vals else 50
        signals.append(("humidité", avg_hum, avg_hum < 30))

        ndvi_vals = list(VegetationObservation.objects.filter(
            zone=zone, index_name="NDVI",
            acquisition_date__gte=(now - timedelta(days=14)).date()
        ).values_list("value", flat=True))
        avg_ndvi = sum(ndvi_vals) / len(ndvi_vals) if ndvi_vals else 0.5
        signals.append(("NDVI", avg_ndvi, avg_ndvi < 0.3))

        triggered_count = sum(1 for _, _, t in signals if t)
        triggered = triggered_count >= 3  # Need at least 3 of 4 signals

        return {
            "triggered": triggered,
            "signals": {s[0]: s[1] for s in signals},
            "triggered_count": triggered_count,
            "description": f"Signaux: {', '.join(s[0] for s in signals if s[2])}",
        }

    def _count_recent_fires(self, zone, days=3) -> int:
        from apps.fires.models import FireDetection
        return FireDetection.objects.filter(
            zone=zone, detected_at__gte=timezone.now() - timedelta(days=days)
        ).count()

    def _check_precipitation_deficit(self, zone) -> Dict[str, Any]:
        from apps.climate.models import ClimateObservation
        vals = list(ClimateObservation.objects.filter(
            zone=zone, variable="PRECIPITATION",
            observed_at__gte=timezone.now() - timedelta(days=30)
        ).values_list("value", flat=True))
        total = sum(vals) if vals else 0
        triggered = len(vals) > 0 and total < 20  # Less than 20mm in 30 days
        return {
            "triggered": triggered,
            "total_30d": total,
            "description": f"Précipitations 30j: {total:.1f}mm (seuil: 20mm)",
        }

    def _check_extreme_heat(self, zone) -> Dict[str, Any]:
        from apps.climate.models import ClimateObservation
        vals = list(ClimateObservation.objects.filter(
            zone=zone, variable="TEMPERATURE",
            observed_at__gte=timezone.now() - timedelta(days=3)
        ).values_list("value", flat=True))
        max_temp = max(vals) if vals else 0
        triggered = max_temp > 45
        return {
            "triggered": triggered,
            "max_temp": max_temp,
            "description": f"Température max: {max_temp:.1f}°C (seuil: 45°C)",
        }

    def _check_vegetation_decline(self, zone) -> Dict[str, Any]:
        from apps.vegetation.models import VegetationObservation
        recent = list(VegetationObservation.objects.filter(
            zone=zone, index_name="NDVI",
            acquisition_date__gte=(timezone.now() - timedelta(days=14)).date()
        ).values_list("value", flat=True))
        older = list(VegetationObservation.objects.filter(
            zone=zone, index_name="NDVI",
            acquisition_date__gte=(timezone.now() - timedelta(days=60)).date(),
            acquisition_date__lt=(timezone.now() - timedelta(days=14)).date()
        ).values_list("value", flat=True))

        if not recent or not older:
            return {"triggered": False}

        avg_recent = sum(recent) / len(recent)
        avg_older = sum(older) / len(older)
        decline = avg_older - avg_recent
        triggered = decline > 0.15  # More than 15% decline

        return {
            "triggered": triggered,
            "avg_recent": avg_recent,
            "avg_older": avg_older,
            "decline": decline,
            "description": f"NDVI: {avg_recent:.3f} vs {avg_older:.3f} (baisse: {decline:.3f})",
        }

    def _check_water_pollution(self, zone) -> Dict[str, Any]:
        from apps.water.models import WaterObservation
        now = timezone.now()

        ph_vals = list(WaterObservation.objects.filter(
            water_body__zone=zone, metric="PH",
            measured_at__gte=now - timedelta(days=7)
        ).values_list("value", flat=True))
        turb_vals = list(WaterObservation.objects.filter(
            water_body__zone=zone, metric="TURBIDITY",
            measured_at__gte=now - timedelta(days=7)
        ).values_list("value", flat=True))

        issues = []
        if ph_vals:
            avg_ph = sum(ph_vals) / len(ph_vals)
            if avg_ph < 6.5 or avg_ph > 8.5:
                issues.append(f"pH={avg_ph:.1f}")
        if turb_vals:
            avg_turb = sum(turb_vals) / len(turb_vals)
            if avg_turb > 100:
                issues.append(f"Turbidité={avg_turb:.0f}NTU")

        triggered = len(issues) > 0
        return {
            "triggered": triggered,
            "issues": issues,
            "description": f"Anomalies eau: {', '.join(issues)}" if issues else "Eau normale",
        }

    def _check_flood_warning(self, zone) -> Dict[str, Any]:
        """Check hydrological flood risks from GloFAS and LANCE Flood."""
        from apps.water.models import RiverForecast, FloodObservation, HydrologicalStation
        from django.db.models import Q

        now = timezone.now()
        station = HydrologicalStation.objects.filter(
            Q(zone=zone) | Q(nom__icontains=zone.name.split()[0])
        ).first()

        glofas_alert = False
        discharge = 0.0
        if station:
            f = RiverForecast.objects.filter(
                station=station,
                date_run__gte=(now - timedelta(days=3)).date()
            ).order_by("-date_run", "leadtime_hours").first()
            if f and (f.discharge_m3s >= station.seuil_alerte or f.alert_level in ["ORANGE", "RED"]):
                glofas_alert = True
                discharge = f.discharge_m3s

        floods = FloodObservation.objects.filter(
            Q(zone=zone) | Q(zone__isnull=True),
            observation_date__gte=(now - timedelta(days=5)).date()
        ).order_by("-observation_date")
        flooded_km2 = floods.first().flooded_area_km2 if floods.exists() else 0.0

        triggered = glofas_alert or (flooded_km2 >= 10.0)
        sev = "CRITICAL" if (glofas_alert and flooded_km2 >= 5.0) else "HIGH"

        return {
            "triggered": triggered,
            "severity": sev,
            "discharge_m3s": discharge,
            "flooded_area_km2": flooded_km2,
            "description": f"Risque de crue/inondation : Débit {discharge:.0f} m³/s, {flooded_km2:.1f} km² sous eau observés.",
        }

    @staticmethod
    def _make_alert(zone, rule_name, title, description, severity, source, metadata=None):
        """Create alert data dict."""
        return {
            "rule_name": rule_name,
            "alert_type": rule_name.split("_")[0] if "_" in rule_name else "GENERAL",
            "title": title,
            "description": description,
            "severity": severity,
            "source": source,
            "zone": zone,
            "metadata": metadata or {},
        }
