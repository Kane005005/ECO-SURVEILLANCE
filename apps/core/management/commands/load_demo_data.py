"""
Management command to load demo data for ECO-SURVEILLANCE MALI.
All data is clearly marked as simulated.
"""
import random
from datetime import timedelta
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.utils import timezone


class Command(BaseCommand):
    help = "Load complete demo data for ECO-SURVEILLANCE MALI"

    def handle(self, *args, **options):
        self.stdout.write("Loading demo data...")
        self._create_geography()
        self._create_stations()
        self._create_observations()
        self._create_fires()
        self._create_anomalies_and_risks()
        self._create_incidents_and_alerts()
        self._create_iez()
        self._create_data_sources()
        self.stdout.write(self.style.SUCCESS("Demo data loaded successfully!"))

    def _create_geography(self):
        from apps.geography.models import Country, Region, Circle, Commune, MonitoringZone

        country, _ = Country.objects.get_or_create(code="MLI", defaults={"name": "Mali"})

        regions_data = [
            ("Bamako", "BKO", "Bamako", 246.0, 2710000),
            ("Sikasso", "SIK", "Sikasso", 7028.0, 2620000),
            ("Segou", "SEG", "Segou", 25315.0, 2336000),
            ("Mopti", "MOP", "Mopti", 79017.0, 2037000),
            ("Koulikoro", "KOU", "Koulikoro", 79654.0, 2418000),
            ("Tombouctou", "TOM", "Tombouctou", 40947.0, 681000),
            ("Gao", "GAO", "Gao", 101300.0, 544000),
            ("Kidal", "KID", "Kidal", 113000.0, 67000),
        ]

        regions = {}
        for name, code, capital, area, pop in regions_data:
            r, _ = Region.objects.get_or_create(
                code=code, defaults={"name": name, "country": country, "capital": capital, "area_km2": area, "population": pop}
            )
            regions[code] = r

        circles_data = [
            ("Koulikoro", "KOU", "KOU"), ("Banamba", "BAN", "BKO"),
            ("Segou", "SEGC", "SEG"), ("Macina", "MAC", "MOP"),
            ("Mopti", "MOPC", "MOP"), ("Sikasso", "SIKC", "SIK"),
            ("Kadiolo", "KAD", "SIK"), ("Bamako", "BKOC", "BKO"),
        ]

        circles = {}
        for name, code, rc in circles_data:
            c, _ = Circle.objects.get_or_create(
                code=code, defaults={"name": name, "region": regions.get(rc, regions["BKO"])}
            )
            circles[code] = c

        communes_data = [
            ("Bamako", "BKM", 12.6392, -8.0029, "BKOC"),
            ("Koulikoro", "KOM", 12.8628, -7.5597, "KOU"),
            ("Segou", "SEM", 13.4400, -6.2600, "SEGC"),
            ("Mopti", "MOM", 14.4844, -4.1830, "MOPC"),
            ("Sikasso", "SIM", 11.3175, -5.6664, "SIKC"),
            ("Timbouctou", "TIM", 16.7666, -3.0074, "KOU"),
            ("Gao", "GAM", 16.2717, -1.5310, "KOU"),
        ]

        for name, code, lat, lng, cc in communes_data:
            Commune.objects.get_or_create(
                code=code, defaults={"name": name, "circle": circles.get(cc, circles["KOU"]), "latitude": lat, "longitude": lng}
            )

        zones_data = [
            ("Bamako Centre", "URBAN", 12.6392, -8.0029, "BKO"),
            ("Delta du Niger", "WETLAND", 14.2000, -4.8000, "MOP"),
            ("Plaines de Segou", "AGRICULTURAL", 13.8000, -6.0000, "SEG"),
            ("Foret de Sikasso", "FOREST", 11.3500, -5.7000, "SIK"),
            ("Sahel de Tombouctou", "SAVANNAH", 16.5000, -3.5000, "TOM"),
            ("Zone urbaine Mopti", "URBAN", 14.4844, -4.1830, "MOP"),
            ("Barrage de Selingue", "LAKE", 11.7500, -7.9500, "SIK"),
            ("Vallee du Niger", "RIVER", 14.0000, -5.5000, "SEG"),
            ("Steppe de Gao", "DESERT", 16.5000, -1.0000, "GAO"),
            ("Zone agricole Koulikoro", "AGRICULTURAL", 12.9000, -7.6000, "KOU"),
            ("Boucle du Niger", "WETLAND", 15.0000, -4.0000, "MOP"),
            ("Foret classee de Banamba", "FOREST", 13.5500, -7.4500, "BKO"),
        ]

        zones = []
        for name, ztype, lat, lng, rc in zones_data:
            ie = round(random.uniform(30, 95), 1)
            status = "NORMAL" if ie >= 85 else "MONITORING" if ie >= 65 else "ALERT" if ie >= 40 else "CRITICAL"
            vuln = "LOW" if ie >= 85 else "MEDIUM" if ie >= 65 else "HIGH" if ie >= 40 else "CRITICAL"
            z, _ = MonitoringZone.objects.get_or_create(
                name=name, defaults={
                    "zone_type": ztype, "latitude": lat, "longitude": lng,
                    "area_km2": round(random.uniform(100, 5000), 1),
                    "population": random.randint(10000, 500000),
                    "vulnerability_level": vuln, "current_iez": ie, "status": status,
                    "region": regions.get(rc, regions["BKO"]), "is_simulated": True,
                }
            )
            zones.append(z)

        self.stdout.write(f"  Geography: 1 country, {len(regions)} regions, {len(circles)} circles, "
                          f"{Commune.objects.count()} communes, {len(zones)} zones")

    def _create_stations(self):
        from apps.sensors.models import MonitoringStation, Sensor, SensorType
        from apps.geography.models import MonitoringZone

        zones = list(MonitoringZone.objects.all())
        sensors_to_create = []
        stations = []
        scode = 1

        for zone in zones:
            for i in range(2):
                code = f"ST-{scode:04d}"
                s, created = MonitoringStation.objects.get_or_create(
                    code=code, defaults={
                        "name": f"Station {zone.name} {i + 1}", "zone": zone,
                        "latitude": zone.latitude + random.uniform(-0.1, 0.1),
                        "longitude": zone.longitude + random.uniform(-0.1, 0.1),
                        "status": "ACTIVE", "is_simulated": True,
                        "battery_level": random.randint(40, 100),
                        "last_seen_at": timezone.now() - timedelta(minutes=random.randint(1, 120)),
                    }
                )
                if created:
                    stations.append(s)
                    for stype, unit in [
                        (SensorType.TEMPERATURE, "C"), (SensorType.PH, ""),
                        (SensorType.TURBIDITY, "NTU"), (SensorType.CONDUCTIVITY, "uS/cm"),
                        (SensorType.DISSOLVED_OXYGEN, "mg/L"), (SensorType.WATER_LEVEL, "m"),
                    ]:
                        sensors_to_create.append(Sensor(
                            station=s, sensor_type=stype,
                            code=f"{stype}_{code}", unit=unit, is_active=True
                        ))
                scode += 1

        Sensor.objects.bulk_create(sensors_to_create, ignore_conflicts=True)
        self.stdout.write(f"  Stations: {MonitoringStation.objects.count()}, Sensors: {Sensor.objects.count()}")

    def _create_observations(self):
        from apps.geography.models import MonitoringZone
        from apps.vegetation.models import VegetationObservation
        from apps.water.models import WaterBody, WaterObservation
        from apps.climate.models import ClimateObservation
        from apps.atmosphere.models import AtmosphericObservation
        from apps.sensors.models import MonitoringStation, Sensor, SensorReading
        import random as rnd

        zones = list(MonitoringZone.objects.all())
        now = timezone.now()

        veg = []
        climate = []
        atmo = []
        water_bodies_to_create = []
        water_obs = []

        for zone in zones:
            for d in range(30):
                date = now - timedelta(days=d)
                v = round(rnd.uniform(0.2, 0.8), 3)
                veg.append(VegetationObservation(
                    zone=zone, index_name="NDVI", value=v,
                    baseline_value=round(v + rnd.uniform(-0.1, 0.1), 3),
                    std_dev=round(rnd.uniform(0.05, 0.15), 3),
                    acquisition_date=date.date(), source="Sentinel-2", is_simulated=True,
                ))
                for var, unit, lo, hi in [
                    ("TEMPERATURE", "C", 25, 45), ("PRECIPITATION", "mm", 0, 50),
                    ("HUMIDITY", "%", 20, 90), ("WIND_SPEED", "m/s", 0, 15),
                ]:
                    climate.append(ClimateObservation(
                        zone=zone, variable=var, value=round(rnd.uniform(lo, hi), 1),
                        unit=unit, observed_at=date, source="NASA POWER", is_simulated=True,
                    ))
                for var, unit, lo, hi in [("NO2", "ug/m3", 5, 80), ("PM25", "ug/m3", 5, 80)]:
                    atmo.append(AtmosphericObservation(
                        zone=zone, variable=var, value=round(rnd.uniform(lo, hi), 1),
                        unit=unit, observed_at=date, source="Sentinel-5P", is_simulated=True,
                    ))

        VegetationObservation.objects.bulk_create(veg, ignore_conflicts=True)
        ClimateObservation.objects.bulk_create(climate, ignore_conflicts=True)
        AtmosphericObservation.objects.bulk_create(atmo, ignore_conflicts=True)

        for zone in zones[:6]:
            wb, created = WaterBody.objects.get_or_create(
                name=f"Eau {zone.name}",
                defaults={"body_type": "RIVER", "zone": zone, "latitude": zone.latitude, "longitude": zone.longitude, "is_simulated": True},
            )
            for d in range(30):
                date = now - timedelta(days=d)
                for metric, unit, lo, hi in [
                    ("TEMPERATURE", "C", 20, 35), ("PH", "", 6.0, 8.0),
                    ("TURBIDITY", "NTU", 10, 100), ("DISSOLVED_OXYGEN", "mg/L", 3, 8),
                ]:
                    water_obs.append(WaterObservation(
                        water_body=wb, metric=metric, value=round(rnd.uniform(lo, hi), 2),
                        unit=unit, measured_at=date, source="Sensor", is_simulated=True,
                    ))

        WaterObservation.objects.bulk_create(water_obs, ignore_conflicts=True)

        readings_to_create = []
        sensors = list(Sensor.objects.select_related("station").all())
        for sensor in sensors:
            for d in range(7):
                date = now - timedelta(days=d)
                val = round(rnd.uniform(20, 35), 2) if "TEMP" in sensor.sensor_type else round(rnd.uniform(5, 8), 2)
                readings_to_create.append(SensorReading(
                    sensor=sensor, value=val, recorded_at=date, is_simulated=True,
                ))

        SensorReading.objects.bulk_create(readings_to_create, ignore_conflicts=True)

        self.stdout.write(f"  Observations: Veg={VegetationObservation.objects.count()}, "
                          f"Climate={ClimateObservation.objects.count()}, "
                          f"Atmo={AtmosphericObservation.objects.count()}, "
                          f"Water={WaterObservation.objects.count()}, "
                          f"Readings={SensorReading.objects.count()}")

    def _create_fires(self):
        from apps.fires.models import FireDetection
        from apps.geography.models import MonitoringZone

        zones = list(MonitoringZone.objects.all())
        now = timezone.now()
        fires = []

        for i in range(60):
            zone = random.choice(zones)
            days_ago = random.randint(0, 14)
            fires.append(FireDetection(
                latitude=zone.latitude + random.uniform(-2, 2),
                longitude=zone.longitude + random.uniform(-2, 2),
                detected_at=now - timedelta(days=days_ago, hours=random.randint(0, 23)),
                satellite=random.choice(["MODIS", "VIIRS"]),
                confidence=random.choice(["low", "nominal", "high"]),
                brightness=round(random.uniform(300, 500), 1),
                frp=round(random.uniform(5, 200), 1),
                source="NASA FIRMS (simule)", is_simulated=True, zone=zone,
            ))

        FireDetection.objects.bulk_create(fires)
        self.stdout.write(f"  Fires: {FireDetection.objects.count()}")

    def _create_anomalies_and_risks(self):
        from apps.anomalies.models import Anomaly
        from apps.risk.models import RiskAssessment
        from apps.geography.models import MonitoringZone

        zones = list(MonitoringZone.objects.all())
        now = timezone.now()
        anomalies = []
        risks = []

        for zone in zones:
            for d in range(10):
                if random.random() > 0.6:
                    atype = random.choice(["VEGETATION", "WATER", "FIRE", "CLIMATE", "ATMOSPHERE"])
                    sev = random.choice(["LOW", "MEDIUM", "HIGH", "CRITICAL"])
                    score = round(random.uniform(10, 95), 1)
                    anomalies.append(Anomaly(
                        anomaly_type=atype, zone=zone, source="AnomalyEngine",
                        detected_at=now - timedelta(days=d), severity=sev,
                        score=score, confidence=round(random.uniform(0.3, 0.95), 2),
                        metric=f"metric_{atype.lower()}",
                        current_value=round(random.uniform(0, 100), 2),
                        baseline_value=round(random.uniform(0, 100), 2),
                        z_score=round(random.uniform(-4, 4), 2),
                        status=random.choice(["NEW", "INVESTIGATING", "CONFIRMED"]),
                        is_simulated=True,
                    ))

            for rtype in ["WILDFIRE", "DROUGHT", "VEGETATION_DEGRADATION", "WATER_POLLUTION", "WATER_STRESS", "HEAT"]:
                rs = round(random.uniform(5, 95), 1)
                cs = round(random.uniform(30, 95), 1)
                level = "RED" if rs >= 80 else "ORANGE" if rs >= 50 else "YELLOW" if rs >= 25 else "GREEN"
                risks.append(RiskAssessment(
                    zone=zone, risk_type=rtype, risk_score=rs, confidence_score=cs,
                    level=level, severity={"GREEN": "LOW", "YELLOW": "MEDIUM", "ORANGE": "HIGH", "RED": "CRITICAL"}[level],
                    factors=[{"source": "demo"}], calculated_at=now, is_simulated=True,
                ))

        Anomaly.objects.bulk_create(anomalies)
        RiskAssessment.objects.bulk_create(risks)
        self.stdout.write(f"  Anomalies: {Anomaly.objects.count()}, Risks: {RiskAssessment.objects.count()}")

    def _create_incidents_and_alerts(self):
        from apps.incidents.models import Incident
        from apps.alerts.models import Alert
        from apps.geography.models import MonitoringZone
        from apps.users.models import User

        zones = list(MonitoringZone.objects.all())
        now = timezone.now()
        admin_user = User.objects.filter(is_superuser=True).first()

        incidents = []
        for title, itype, severity, desc in [
            ("Canicule severe a Bamako", "HEAT", "CRITICAL", "Temperatures extremes detectees"),
            ("Feu de foret dans la zone Sikasso", "WILDFIRE", "HIGH", "Hotspots FIRMS actifs"),
            ("Secheresse Delta du Niger", "DROUGHT", "HIGH", "Deficit pluviometrique important"),
            ("Pollution eau Segou", "WATER_POLLUTION", "MEDIUM", "Turbidite et pH anormaux"),
            ("Degradation vegetation Tombouctou", "VEGETATION_DEGRADATION", "MEDIUM", "NDVI en baisse significative"),
            ("Stress hydrique Koulikoro", "WATER_STRESS", "HIGH", "Niveau bas des cours d'eau"),
            ("Anomalie atmospherique Mopti", "ATMOSPHERIC_ANOMALY", "LOW", "NO2 eleve detecte"),
            ("Incendie rural Banamba", "WILDFIRE", "CRITICAL", "Plusieurs foyers actifs"),
        ]:
            zone = random.choice(zones)
            incidents.append(Incident(
                title=title, incident_type=itype, description=desc, zone=zone,
                latitude=zone.latitude, longitude=zone.longitude, severity=severity,
                risk_score=round(random.uniform(40, 95), 1),
                confidence_score=round(random.uniform(50, 95), 1),
                source="AnomalyEngine + RiskEngine",
                detected_at=now - timedelta(days=random.randint(0, 10)),
                status=random.choice(["NEW", "INVESTIGATING", "CONFIRMED"]),
                assigned_to=admin_user, is_simulated=True,
            ))

        Incident.objects.bulk_create(incidents)

        alerts = []
        if admin_user:
            for inc in Incident.objects.all()[:5]:
                alerts.append(Alert(
                    incident=inc, recipient=admin_user, channel="WEB",
                    severity=inc.severity,
                    message=f"Alerte: {inc.title} - {inc.description}",
                    sent_at=now - timedelta(hours=random.randint(1, 48)),
                    read_at=now - timedelta(hours=random.randint(0, 24)) if random.random() > 0.3 else None,
                    status="SENT", is_simulated=True,
                ))
        Alert.objects.bulk_create(alerts)
        self.stdout.write(f"  Incidents: {Incident.objects.count()}, Alerts: {Alert.objects.count()}")

    def _create_iez(self):
        from apps.iez.models import IEZCalculation
        from apps.iez.services import IEZCalculationService
        from apps.geography.models import MonitoringZone

        zones = list(MonitoringZone.objects.all())
        service = IEZCalculationService()

        for zone in zones:
            components = {
                "vegetation": round(random.uniform(30, 95), 1),
                "water": round(random.uniform(25, 90), 1),
                "climate": round(random.uniform(40, 85), 1),
                "fire": round(random.uniform(50, 95), 1),
                "atmosphere": round(random.uniform(40, 80), 1),
                "human_pressure": round(random.uniform(30, 70), 1),
                "vulnerability": round(random.uniform(35, 80), 1),
            }
            service.calculate_zone_iez(zone, components)

        self.stdout.write(f"  IEZ calculations: {IEZCalculation.objects.count()}")

    def _create_data_sources(self):
        from apps.core.models import DataSource

        for name, provider, stype, desc, status in [
            ("NASA FIRMS", "NASA FIRMS", "FIRE", "Detection de feux actifs", "ACTIVE"),
            ("Sentinel-2", "Copernicus", "SATELLITE", "Images satellite", "NOT_CONFIGURED"),
            ("Sentinel-5P", "Copernicus", "ATMOSPHERE", "Donnees atmospheriques", "NOT_CONFIGURED"),
            ("NASA POWER", "NASA", "CLIMATE", "Donnees climatiques", "NOT_CONFIGURED"),
            ("ERA5", "Copernicus", "CLIMATE", "Reanalyse climatique", "NOT_CONFIGURED"),
            ("CHIRPS", "UCSB", "CLIMATE", "Precipitations satellite", "NOT_CONFIGURED"),
            ("Groq AI", "Groq", "AI", "Analyse IA contextuelle", "ACTIVE"),
            ("Capteurs IoT", "Simulated", "SENSOR", "Stations simulees", "ACTIVE"),
        ]:
            DataSource.objects.get_or_create(
                name=name, defaults={"provider": provider, "source_type": stype, "description": desc, "status": status, "is_simulated": stype == "SENSOR"},
            )

        self.stdout.write(f"  Data sources: {DataSource.objects.count()}")
