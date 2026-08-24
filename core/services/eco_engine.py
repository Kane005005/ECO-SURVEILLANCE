"""
Central ECO Engine & Multi-Source Cross-Correlation Service.
Orchestrates multi-sensor data fusion (GloFAS, LANCE Flood, FIRMS, NASA POWER, Sentinel-2/5P, OpenAQ)
and generates cross-correlated alerts with explainable AI context notes (Groq AI).
"""
import logging
from typing import Dict, Any, List, Optional
from datetime import timedelta, date
from django.utils import timezone
from django.db.models import Q, Avg, Sum, Max

from ai.groq import GroqProvider

logger = logging.getLogger("apps.alerts")


class ECOEngine:
    """
    Moteur central de corrélation croisée multi-sources pour ECO-SURVEILLANCE MALI.
    """

    def __init__(self, ai_provider: Optional[GroqProvider] = None):
        self.ai = ai_provider or GroqProvider()

    def run_all_correlations(self) -> List[Dict[str, Any]]:
        """Évalue l'ensemble des règles de corrélation croisée sur tout le Mali."""
        from apps.geography.models import MonitoringZone

        all_triggered = []
        zones = MonitoringZone.objects.all()

        for zone in zones:
            try:
                zone_alerts = self.evaluate_zone_correlations(zone)
                all_triggered.extend(zone_alerts)
            except Exception as e:
                logger.error("Erreur lors de l'évaluation ECO Engine pour la zone %s: %s", zone.name, str(e))

        logger.info("ECO Engine a généré %d alertes corrélées.", len(all_triggered))
        return all_triggered

    def evaluate_zone_correlations(self, zone) -> List[Dict[str, Any]]:
        """Évalue les 4 règles maîtresses de corrélation croisée pour une zone donnée."""
        triggered = []

        # Règle 1 : Crue confirmée (GloFAS + LANCE Flood)
        flood_res = self._check_rule1_flood_confirmation(zone)
        if flood_res.get("triggered"):
            alert_obj = self._create_correlated_incident_and_alert(
                zone=zone,
                incident_type="FLOOD",
                title=f"Alerte Crue Majeure Confirmée — {zone.name}",
                severity="CRITICAL",
                rule_name="CRUE_CONFIRMEE_GLOFAS_LANCE",
                description=flood_res["description"],
                sources=["GloFAS", "NASA LANCE Flood VIIRS", "Sentinel-2 NDWI"],
                signals=flood_res["signals"],
                trigger_sentinel2_ndwi=True,
            )
            triggered.append(alert_obj)

        # Règle 2 : Incendie & Météo Extrême (FIRMS + NASA POWER)
        fire_res = self._check_rule2_fire_extreme_weather(zone)
        if fire_res.get("triggered"):
            alert_obj = self._create_correlated_incident_and_alert(
                zone=zone,
                incident_type="WILDFIRE",
                title=f"Risque Majeur de Propagation Feux de Brousse — {zone.name}",
                severity="CRITICAL" if fire_res.get("is_critical") else "HIGH",
                rule_name="INCENDIE_METEO_EXTREME",
                description=fire_res["description"],
                sources=["NASA FIRMS", "NASA POWER (Météo/Vent)"],
                signals=fire_res["signals"],
            )
            triggered.append(alert_obj)

        # Règle 3 : Sécheresse Agro-Climatique (NASA POWER + Sentinel-2 NDVI)
        drought_res = self._check_rule3_agro_drought(zone)
        if drought_res.get("triggered"):
            alert_obj = self._create_correlated_incident_and_alert(
                zone=zone,
                incident_type="DROUGHT",
                title=f"Alerte Sécheresse Agro-Climatique — {zone.name}",
                severity="HIGH",
                rule_name="SECHERESSE_AGRO_CLIMATIQUE",
                description=drought_res["description"],
                sources=["NASA POWER / CHIRPS", "Sentinel-2 NDVI"],
                signals=drought_res["signals"],
            )
            triggered.append(alert_obj)

        # Règle 4 : Poussière Harmattan & Qualité de l'Air (Sentinel-5P + OpenAQ + Météo)
        air_res = self._check_rule4_harmattan_air_quality(zone)
        if air_res.get("triggered"):
            alert_obj = self._create_correlated_incident_and_alert(
                zone=zone,
                incident_type="ATMOSPHERIC_ANOMALY",
                title=f"Épisode Poussière Harmattan & Pollution — {zone.name}",
                severity="HIGH" if air_res.get("is_high") else "MEDIUM",
                rule_name="POUSSIERE_HARMATTAN_AIR",
                description=air_res["description"],
                sources=["Sentinel-5P Aérosols", "OpenAQ PM2.5", "NASA POWER (Vent Harmattan)"],
                signals=air_res["signals"],
            )
            triggered.append(alert_obj)

        return triggered

    def _check_rule1_flood_confirmation(self, zone) -> Dict[str, Any]:
        """
        RÈGLE 1 : Si débit GloFAS > seuil_alerte (ou trend_72h > +30%)
        ET détection de pixels inondés LANCE Flood > 5 km² dans le secteur.
        """
        from apps.water.models import RiverForecast, FloodObservation, HydrologicalStation

        now = timezone.now()
        station = HydrologicalStation.objects.filter(
            Q(zone=zone) | Q(nom__icontains=zone.name.split()[0])
        ).first()

        glofas_alert = False
        discharge_val = 0.0
        trend_val = 0.0
        threshold_val = 2000.0

        if station:
            threshold_val = station.seuil_alerte
            forecast = RiverForecast.objects.filter(
                station=station,
                date_run__gte=(now - timedelta(days=3)).date()
            ).order_by("-date_run", "leadtime_hours").first()

            if forecast:
                discharge_val = forecast.discharge_m3s
                trend_val = forecast.trend_72h_pct
                if discharge_val >= station.seuil_alerte or trend_val >= 30.0:
                    glofas_alert = True
        else:
            # Check regional GloFAS forecasts
            regional_forecasts = RiverForecast.objects.filter(
                date_run__gte=(now - timedelta(days=3)).date(),
                alert_level__in=["ORANGE", "RED"]
            )
            if regional_forecasts.exists():
                glofas_alert = True
                f = regional_forecasts.first()
                discharge_val = f.discharge_m3s
                trend_val = f.trend_72h_pct

        # Check LANCE Flood observations (> 5 km2)
        floods = FloodObservation.objects.filter(
            Q(zone=zone) | Q(zone__isnull=True),
            observation_date__gte=(now - timedelta(days=5)).date()
        ).order_by("-observation_date")

        max_flooded_km2 = 0.0
        flooded_pixels = 0
        tile_name = "h17v07"
        if floods.exists():
            f_top = floods.first()
            max_flooded_km2 = f_top.flooded_area_km2
            flooded_pixels = f_top.flooded_pixels_count
            tile_name = f_top.tile_name

        lance_flood_alert = (max_flooded_km2 >= 5.0)

        triggered = (glofas_alert and lance_flood_alert)

        return {
            "triggered": triggered,
            "signals": {
                "discharge_m3s": discharge_val,
                "seuil_alerte_m3s": threshold_val,
                "trend_72h_pct": trend_val,
                "flooded_area_km2": max_flooded_km2,
                "flooded_pixels": flooded_pixels,
                "tile_name": tile_name,
            },
            "description": (
                f"Crue hydrologique majeure confirmée par double signal : "
                f"Débit GloFAS prévu de {discharge_val:.0f} m³/s (tendance 72h: +{trend_val:.1f}%) "
                f"corrélé avec {max_flooded_km2:.1f} km² ({max_flooded_km2*100:.0f} ha) de surfaces submergées détectées par NASA LANCE Flood."
            ),
        }

    def _check_rule2_fire_extreme_weather(self, zone) -> Dict[str, Any]:
        """
        RÈGLE 2 : Feux actifs FIRMS + Climat extrême (T° > 38°C, Humidité < 20%, Vent > 6 m/s).
        """
        from apps.fires.models import FireDetection
        from apps.climate.models import ClimateObservation

        now = timezone.now()
        fire_count = FireDetection.objects.filter(
            zone=zone,
            detected_at__gte=now - timedelta(days=3)
        ).count()

        # Climate observations
        temps = list(ClimateObservation.objects.filter(
            zone=zone, variable="TEMPERATURE", observed_at__gte=now - timedelta(days=3)
        ).values_list("value", flat=True))
        max_temp = max(temps) if temps else 32.0

        hums = list(ClimateObservation.objects.filter(
            zone=zone, variable="HUMIDITY", observed_at__gte=now - timedelta(days=3)
        ).values_list("value", flat=True))
        min_hum = min(hums) if hums else 40.0

        winds = list(ClimateObservation.objects.filter(
            zone=zone, variable="WIND_SPEED", observed_at__gte=now - timedelta(days=3)
        ).values_list("value", flat=True))
        max_wind = max(winds) if winds else 3.5

        is_extreme_weather = (max_temp >= 38.0 and min_hum <= 25.0) or (max_wind >= 6.0 and max_temp >= 35.0)
        triggered = (fire_count >= 1 and is_extreme_weather)

        return {
            "triggered": triggered,
            "is_critical": (fire_count >= 3 or (max_temp >= 40.0 and max_wind >= 7.0)),
            "signals": {
                "fire_count_3d": fire_count,
                "max_temperature_c": round(max_temp, 1),
                "min_humidity_pct": round(min_hum, 1),
                "max_wind_speed_ms": round(max_wind, 1),
            },
            "description": (
                f"Forte propagation d'incendie : {fire_count} foyer(s) actif(s) FIRMS "
                f"combiné(s) à des conditions météo critiques (T°: {max_temp:.1f}°C, Humidité: {min_hum:.1f}%, Vent: {max_wind:.1f} m/s)."
            ),
        }

    def _check_rule3_agro_drought(self, zone) -> Dict[str, Any]:
        """
        RÈGLE 3 : Déficit pluviométrique 30j NASA POWER/CHIRPS + Baisse NDVI Sentinel-2.
        """
        from apps.climate.models import ClimateObservation
        from apps.vegetation.models import VegetationObservation

        now = timezone.now()
        precip_vals = list(ClimateObservation.objects.filter(
            zone=zone, variable="PRECIPITATION", observed_at__gte=now - timedelta(days=30)
        ).values_list("value", flat=True))
        total_precip_30d = sum(precip_vals) if precip_vals else 10.0

        ndvi_recent = list(VegetationObservation.objects.filter(
            zone=zone, index_name="NDVI", acquisition_date__gte=(now - timedelta(days=14)).date()
        ).values_list("value", flat=True))
        avg_ndvi = sum(ndvi_recent) / len(ndvi_recent) if ndvi_recent else 0.30

        is_precip_deficit = total_precip_30d <= 25.0
        is_vegetation_stressed = avg_ndvi <= 0.35

        triggered = (is_precip_deficit and is_vegetation_stressed)

        return {
            "triggered": triggered,
            "signals": {
                "precip_30d_mm": round(total_precip_30d, 1),
                "ndvi_current": round(avg_ndvi, 3),
            },
            "description": (
                f"Stress hydrique & sécheresse agro-climatique avérée : "
                f"Cumul pluviométrique 30j de seulement {total_precip_30d:.1f} mm "
                f"et indice de vitalité végétale NDVI très bas ({avg_ndvi:.3f})."
            ),
        }

    def _check_rule4_harmattan_air_quality(self, zone) -> Dict[str, Any]:
        """
        RÈGLE 4 : Aérosols Sentinel-5P + PM2.5 OpenAQ > 75 µg/m³ + Vent Harmattan NASA POWER.
        """
        from apps.atmosphere.models import AtmosphericObservation
        from apps.climate.models import ClimateObservation

        now = timezone.now()
        pm25_vals = list(AtmosphericObservation.objects.filter(
            zone=zone, variable="PM25", observed_at__gte=now - timedelta(days=3)
        ).values_list("value", flat=True))
        max_pm25 = max(pm25_vals) if pm25_vals else 0.0

        aerosol_vals = list(AtmosphericObservation.objects.filter(
            zone=zone, variable__in=["AEROSOL", "AER_AI", "NO2"], observed_at__gte=now - timedelta(days=3)
        ).values_list("value", flat=True))
        avg_aerosol = sum(aerosol_vals) / len(aerosol_vals) if aerosol_vals else 0.0

        wind_vals = list(ClimateObservation.objects.filter(
            zone=zone, variable="WIND_SPEED", observed_at__gte=now - timedelta(days=3)
        ).values_list("value", flat=True))
        max_wind = max(wind_vals) if wind_vals else 4.0

        is_high_pm = max_pm25 >= 75.0 or avg_aerosol >= 1.5
        is_harmattan_wind = max_wind >= 4.0

        triggered = (is_high_pm and is_harmattan_wind)

        return {
            "triggered": triggered,
            "is_high": max_pm25 >= 100.0,
            "signals": {
                "max_pm25": round(max_pm25, 1),
                "aerosol_index": round(avg_aerosol, 2),
                "max_wind_speed": round(max_wind, 1),
            },
            "description": (
                f"Pic de pollution aux poussières désertiques (Harmattan) : "
                f"PM2.5 à {max_pm25:.1f} µg/m³ et aérosols renforcés par des vents de {max_wind:.1f} m/s."
            ),
        }

    def _generate_ai_explanation(self, incident_title: str, severity: str, sources: List[str], signals: Dict[str, Any], zone_name: str) -> str:
        """Génère une synthèse explicative d'aide à la décision en français via Groq AI."""
        context = {
            "incident": incident_title,
            "zone": zone_name,
            "severite": severity,
            "sources_combinees": sources,
            "signaux_physiques": signals,
            "pays": "Mali (Sahel / UEMOA)",
        }

        try:
            res = self.ai.interpret_incident(context)
            if res.get("summary") and not res.get("error"):
                return res["summary"].strip()
        except Exception as e:
            logger.warning("Groq AI context call fallback: %s", str(e))

        # Fallback analytique structuré expert
        return (
            f"Analyse ECO Engine ({', '.join(sources)}) : Alerte {severity} détectée sur la zone {zone_name}. "
            f"La corrélation de plusieurs capteurs confirme une anomalie environnementale critique. "
            f"Recommandation opérationnelle : mobilisation des cellules de veille locale, diffusion des consignes de sécurité "
            f"et surveillance renforcée des évolutions satellitaires et hydrométriques à 24-72h."
        )

    def _create_correlated_incident_and_alert(
        self,
        zone,
        incident_type: str,
        title: str,
        severity: str,
        rule_name: str,
        description: str,
        sources: List[str],
        signals: Dict[str, Any],
        trigger_sentinel2_ndwi: bool = False,
    ) -> Dict[str, Any]:
        """Crée l'incident, l'alerte et planifie les tâches satellitaires déclenchées."""
        from apps.incidents.models import Incident
        from apps.alerts.models import Alert
        from apps.users.models import User
        from apps.satellite.models import SatelliteObservation

        now = timezone.now()

        # Deduplication (avoid creating duplicate identical incident in last 24h)
        recent_incident = Incident.objects.filter(
            zone=zone,
            incident_type=incident_type,
            detected_at__gte=now - timedelta(hours=24)
        ).first()

        # Generate AI explanation note
        ai_note = self._generate_ai_explanation(title, severity, sources, signals, zone.name)

        if not recent_incident:
            incident = Incident.objects.create(
                title=title,
                incident_type=incident_type,
                description=f"{description}\n\n[Note Analytique IA (Groq)] :\n{ai_note}",
                zone=zone,
                latitude=zone.latitude,
                longitude=zone.longitude,
                severity=severity,
                risk_score=90.0 if severity == "CRITICAL" else 75.0,
                confidence_score=0.92,
                source=f"ECO-Engine ({' + '.join(sources)})",
                detected_at=now,
                status="NEW",
                is_simulated=False,
                metadata={
                    "rule_name": rule_name,
                    "combined_sources": sources,
                    "signals": signals,
                    "ai_explanation": ai_note,
                },
            )
        else:
            incident = recent_incident

        # Create alert for users
        admin_user = User.objects.filter(is_superuser=True).first()
        if admin_user:
            Alert.objects.get_or_create(
                incident=incident,
                recipient=admin_user,
                defaults={
                    "channel": "WEB",
                    "severity": severity,
                    "message": f"[{severity}] {title} — {description}",
                    "sent_at": now,
                    "status": "SENT",
                    "is_simulated": False,
                }
            )

        # Trigger automatic targeted Sentinel-2 NDWI acquisition task if flood confirmed
        if trigger_sentinel2_ndwi:
            SatelliteObservation.objects.get_or_create(
                zone=zone,
                satellite="SENTINEL2",
                product_type="L2A",
                acquisition_time=now,
                defaults={
                    "source": "Sentinel-2 NDWI Triggered (10m)",
                    "cloud_cover": 5.0,
                    "is_simulated": False,
                    "metadata": {
                        "trigger_reason": "ECO_ENGINE_FLOOD_CONFIRMATION",
                        "index_target": "NDWI_10M",
                        "incident_id": incident.id,
                    }
                }
            )
            logger.info("Déclenchement automatique de la tâche Sentinel-2 NDWI pour la zone inondée: %s", zone.name)

        return {
            "incident_id": incident.id,
            "title": title,
            "severity": severity,
            "rule_name": rule_name,
            "zone": zone.name,
            "sources": sources,
            "ai_explanation": ai_note,
            "signals": signals,
            "created_at": now.isoformat(),
        }
