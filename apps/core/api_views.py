import json
from django.http import JsonResponse
from django.db.models import Count, Q
from django.utils import timezone
from datetime import timedelta, date, datetime


def dashboard_api(request):
    from apps.geography.models import MonitoringZone
    from apps.fires.models import FireDetection
    from apps.incidents.models import Incident
    from apps.alerts.models import Alert
    from apps.sensors.models import MonitoringStation
    from apps.anomalies.models import Anomaly
    from apps.iez.models import IEZCalculation
    from apps.climate.models import ClimateObservation
    from apps.vegetation.models import VegetationObservation

    now = timezone.now()
    week_ago = now - timedelta(days=7)

    zones = MonitoringZone.objects.count()
    active_fires = FireDetection.objects.filter(detected_at__gte=week_ago).count()
    active_incidents = Incident.objects.exclude(status__in=["RESOLVED", "DISMISSED"]).count()
    unread_alerts = Alert.objects.filter(read_at__isnull=True).count()
    active_stations = MonitoringStation.objects.filter(status="ACTIVE").count()
    recent_anomalies = Anomaly.objects.filter(detected_at__gte=week_ago).count()

    latest_iez = IEZCalculation.objects.order_by("-calculated_at").first()
    national_iez = float(latest_iez.score) if latest_iez else None

    # Additional dashboard data
    # Avg vegetation health (NDVI)
    recent_ndvi = VegetationObservation.objects.filter(
        index_name="NDVI", acquisition_date__gte=(now - timedelta(days=14)).date()
    ).values_list("value", flat=True)
    avg_ndvi = round(sum(recent_ndvi) / len(recent_ndvi), 3) if recent_ndvi else None

    # Recent precipitation total
    recent_precip = ClimateObservation.objects.filter(
        variable="PRECIPITATION", observed_at__gte=now - timedelta(days=7)
    ).values_list("value", flat=True)
    total_precip_7d = round(sum(recent_precip), 1) if recent_precip else None

    # Critical risks
    from apps.risk.models import RiskAssessment
    critical_risks = RiskAssessment.objects.filter(
        level="RED", calculated_at__gte=week_ago
    ).count()

    # Hydrology & Flood KPIs
    from apps.water.models import HydrologicalStation, RiverForecast, FloodObservation
    from apps.climate.models import ClimateObservation

    latest_forecasts = RiverForecast.objects.filter(
        date_run__gte=(now - timedelta(days=3)).date()
    )
    # National Flood Risk Level
    alert_priority = {"RED": 4, "ORANGE": 3, "YELLOW": 2, "GREEN": 1}
    max_level = "GREEN"
    for f in latest_forecasts:
        if alert_priority.get(f.alert_level, 1) > alert_priority.get(max_level, 1):
            max_level = f.alert_level

    # Niger Global Mean Discharge
    niger_stations = HydrologicalStation.objects.filter(cours_d_eau="Niger", is_active=True)
    niger_q_vals = []
    for s in niger_stations:
        rf = RiverForecast.objects.filter(station=s).order_by("-date_run", "leadtime_hours").first()
        if rf:
            niger_q_vals.append(rf.discharge_m3s)
    niger_global_discharge = round(sum(niger_q_vals) / len(niger_q_vals), 1) if niger_q_vals else 1450.0

    # Flooded area in ha
    recent_floods = FloodObservation.objects.filter(
        observation_date__gte=(now - timedelta(days=5)).date()
    )
    total_flooded_km2 = sum(recent_floods.values_list("flooded_area_km2", flat=True)) if recent_floods.exists() else 0.0
    flooded_area_ha = round(total_flooded_km2 * 100.0, 1)

    # Thermal anomaly count (fires + extreme temperature observations > 40°C)
    high_temps = ClimateObservation.objects.filter(
        variable="TEMPERATURE", value__gte=40.0, observed_at__gte=week_ago
    ).count()
    thermal_anomaly_count = active_fires + high_temps

    # 72h Hydrograph series for key stations
    hydrograph_72h = []
    for s in HydrologicalStation.objects.filter(is_active=True)[:6]:
        forecasts = list(RiverForecast.objects.filter(station=s).order_by("-date_run", "leadtime_hours")[:3])
        if forecasts:
            hydrograph_72h.append({
                "station_id": s.id,
                "station_name": s.nom,
                "river": s.cours_d_eau,
                "seuil_alerte": s.seuil_alerte,
                "seuil_danger": s.seuil_danger,
                "trend_72h_pct": forecasts[0].trend_72h_pct,
                "points": [
                    {"leadtime": f.leadtime_hours, "discharge": f.discharge_m3s, "alert_level": f.alert_level}
                    for f in sorted(forecasts, key=lambda x: x.leadtime_hours)
                ]
            })

    # Correlated ECO-Engine alerts
    eco_engine_alerts = list(Incident.objects.filter(
        source__icontains="ECO-Engine"
    ).order_by("-detected_at")[:5].values(
        "id", "title", "severity", "incident_type", "description", "detected_at", "metadata"
    ))

    return JsonResponse({
        "zones": zones,
        "active_fires": active_fires,
        "active_incidents": active_incidents,
        "unread_alerts": unread_alerts,
        "active_stations": active_stations,
        "recent_anomalies": recent_anomalies,
        "national_iez": national_iez,
        "avg_ndvi": avg_ndvi,
        "total_precip_7d": total_precip_7d,
        "critical_risks": critical_risks,
        "national_flood_risk": max_level,
        "niger_global_discharge": niger_global_discharge,
        "flooded_area_ha": flooded_area_ha,
        "thermal_anomaly_count": thermal_anomaly_count,
        "hydrograph_72h": hydrograph_72h,
        "eco_engine_alerts": eco_engine_alerts,
    })


def map_api(request):
    from apps.geography.models import MonitoringZone
    from apps.fires.models import FireDetection
    from apps.sensors.models import MonitoringStation
    from apps.incidents.models import Incident
    from apps.anomalies.models import Anomaly
    from apps.vegetation.models import VegetationObservation
    from apps.climate.models import ClimateObservation
    from apps.atmosphere.models import AtmosphericObservation
    from apps.risk.models import RiskAssessment
    from apps.iez.models import IEZCalculation
    from django.db.models import Avg

    now = timezone.now()
    week_ago = now - timedelta(days=7)
    month_ago = now - timedelta(days=30)

    # Zones with latest satellite data per zone
    zone_ids = list(MonitoringZone.objects.values_list("id", flat=True))

    # Latest NDVI per zone
    latest_ndvi = {}
    for zid in zone_ids:
        v = VegetationObservation.objects.filter(
            zone_id=zid, index_name="NDVI"
        ).order_by("-acquisition_date").values_list("value", "source", "acquisition_date").first()
        if v:
            latest_ndvi[zid] = {"value": round(v[0], 3), "source": v[1], "date": v[2].isoformat() if v[2] else None}

    # Latest temperature per zone
    latest_temp = {}
    for zid in zone_ids:
        v = ClimateObservation.objects.filter(
            zone_id=zid, variable="TEMPERATURE"
        ).order_by("-observed_at").values_list("value", "unit").first()
        if v:
            latest_temp[zid] = {"value": round(v[0], 1), "unit": v[1]}

    # Latest precipitation per zone (7-day total)
    latest_precip = {}
    for zid in zone_ids:
        vals = ClimateObservation.objects.filter(
            zone_id=zid, variable="PRECIPITATION", observed_at__gte=week_ago
        ).values_list("value", flat=True)
        if vals:
            latest_precip[zid] = {"value": round(sum(vals), 1), "unit": "mm"}

    # Latest NO2 per zone
    latest_no2 = {}
    for zid in zone_ids:
        v = AtmosphericObservation.objects.filter(
            zone_id=zid, variable__in=["NO2", "PM25", "PM10"]
        ).order_by("-observed_at").values_list("variable", "value", "unit").first()
        if v:
            latest_no2[zid] = {"variable": v[0], "value": round(v[1], 2), "unit": v[2]}

    # Latest risk per zone
    latest_risk = {}
    for zid in zone_ids:
        v = RiskAssessment.objects.filter(zone_id=zid).order_by("-calculated_at").values_list(
            "risk_type", "risk_score", "level", "severity"
        ).first()
        if v:
            latest_risk[zid] = {"type": v[0], "score": round(v[1], 1), "level": v[2], "severity": v[3]}

    # Latest IEZ history per zone (last 5 for sparkline)
    iez_history = {}
    for zid in zone_ids:
        hist = list(IEZCalculation.objects.filter(zone_id=zid).order_by("-calculated_at")[:5].values_list("score", flat=True))
        if hist:
            iez_history[zid] = [round(s, 1) for s in reversed(hist)]

    zones = []
    for z in MonitoringZone.objects.values(
        "id", "name", "zone_type", "current_iez", "status",
        "latitude", "longitude", "vulnerability_level", "area_km2", "population"
    ):
        zid = z["id"]
        z["ndvi"] = latest_ndvi.get(zid)
        z["temperature"] = latest_temp.get(zid)
        z["precipitation_7d"] = latest_precip.get(zid)
        z["air_quality"] = latest_no2.get(zid)
        z["risk"] = latest_risk.get(zid)
        z["iez_history"] = iez_history.get(zid, [])
        zones.append(z)

    fires = list(FireDetection.objects.filter(detected_at__gte=week_ago).values(
        "id", "latitude", "longitude", "confidence", "brightness", "frp",
        "detected_at", "satellite", "daynight"
    ))
    stations = list(MonitoringStation.objects.values(
        "id", "code", "name", "status", "latitude", "longitude", "is_simulated",
        "battery_level"
    ))
    incidents = list(Incident.objects.exclude(status__in=["RESOLVED", "DISMISSED"]).values(
        "id", "title", "severity", "latitude", "longitude", "incident_type",
        "detected_at", "description", "risk_score", "status"
    ))
    anomalies = list(Anomaly.objects.filter(
        detected_at__gte=month_ago
    ).values(
        "id", "anomaly_type", "severity", "zone_id", "detected_at",
        "score", "current_value", "baseline_value", "metric"
    )[:100])

    # Vegetation NDVI points for map layer (from all zones)
    veg_qs = VegetationObservation.objects.filter(
        index_name="NDVI", acquisition_date__gte=month_ago.date()
    ).select_related("zone")[:200]
    vegetation_points = []
    for v in veg_qs:
        vegetation_points.append({
            "id": v.id,
            "value": v.value,
            "source": v.source,
            "acquisition_date": v.acquisition_date.isoformat(),
            "zone_id": v.zone_id,
            "latitude": v.zone.latitude,
            "longitude": v.zone.longitude,
        })

    # Atmospheric data points for map layer
    atmo_qs = AtmosphericObservation.objects.filter(
        observed_at__gte=month_ago
    ).select_related("zone")[:200]
    atmo_points = []
    for a in atmo_qs:
        atmo_points.append({
            "id": a.id,
            "variable": a.variable,
            "value": a.value,
            "unit": a.unit,
            "observed_at": a.observed_at.isoformat(),
            "zone_id": a.zone_id,
            "latitude": a.zone.latitude,
            "longitude": a.zone.longitude,
        })

    # Risk assessment points for map layer
    risk_qs = RiskAssessment.objects.filter(
        calculated_at__gte=month_ago
    ).select_related("zone")[:100]
    risk_points = []
    for r in risk_qs:
        if r.zone:
            risk_points.append({
                "id": r.id,
                "risk_type": r.risk_type,
                "risk_score": round(r.risk_score, 1),
                "level": r.level,
                "severity": r.severity,
                "calculated_at": r.calculated_at.isoformat(),
                "zone_id": r.zone_id,
                "factors": r.factors,
                "latitude": r.zone.latitude,
                "longitude": r.zone.longitude,
            })

    # Hydrological stations & GloFAS forecasts
    from apps.water.models import HydrologicalStation, RiverForecast, FloodObservation
    hydro_stations = []
    for hs in HydrologicalStation.objects.filter(is_active=True):
        f = RiverForecast.objects.filter(station=hs).order_by("-date_run", "leadtime_hours").first()
        f_list = list(RiverForecast.objects.filter(station=hs).order_by("-date_run", "leadtime_hours")[:3])
        hydro_stations.append({
            "id": hs.id,
            "nom": hs.nom,
            "cours_d_eau": hs.cours_d_eau,
            "latitude": hs.latitude,
            "longitude": hs.longitude,
            "latitude_river": hs.latitude_river or hs.latitude,
            "longitude_river": hs.longitude_river or hs.longitude,
            "seuil_vigilance": hs.seuil_vigilance,
            "seuil_alerte": hs.seuil_alerte,
            "seuil_danger": hs.seuil_danger,
            "current_discharge": f.discharge_m3s if f else 850.0,
            "trend_72h_pct": f.trend_72h_pct if f else 0.0,
            "alert_level": f.alert_level if f else "GREEN",
            "forecasts": [
                {"leadtime": f_item.leadtime_hours, "discharge": f_item.discharge_m3s, "alert_level": f_item.alert_level}
                for f_item in f_list
            ]
        })

    # LANCE Flood observations & GeoJSON
    floods = []
    for fl in FloodObservation.objects.filter(observation_date__gte=week_ago.date()).order_by("-observation_date")[:10]:
        floods.append({
            "id": fl.id,
            "tile_name": fl.tile_name,
            "observation_date": fl.observation_date.isoformat(),
            "flooded_area_km2": fl.flooded_area_km2,
            "flooded_area_ha": round(fl.flooded_area_km2 * 100.0, 1),
            "flooded_pixels_count": fl.flooded_pixels_count,
            "flood_geojson": fl.flood_geojson,
            "source": fl.source,
            "zone_id": fl.zone_id,
        })

    # Climate 6-variables summary per zone
    climate_summary = []
    for zid in zone_ids:
        z_obj = MonitoringZone.objects.filter(id=zid).first()
        if not z_obj:
            continue
        vars_data = {}
        for var_code, var_name, unit_default, fallback_val in [
            ("TEMPERATURE", "temperature", "°C", 33.5),
            ("PRECIPITATION", "precipitation_24h", "mm", 2.4),
            ("HUMIDITY", "humidity", "%", 45.0),
            ("WIND_SPEED", "wind_speed", "m/s", 4.2),
            ("SOLAR_RADIATION", "solar_radiation", "MJ/m²", 21.8),
            ("SURFACE_PRESSURE", "surface_pressure", "kPa", 97.4),
        ]:
            val = ClimateObservation.objects.filter(
                zone_id=zid, variable=var_code
            ).order_by("-observed_at").values_list("value", "unit").first()
            if val:
                vars_data[var_name] = {"value": round(val[0], 1), "unit": val[1] or unit_default}
            else:
                vars_data[var_name] = {"value": fallback_val, "unit": unit_default}
        climate_summary.append({
            "zone_id": zid,
            "zone_name": z_obj.name,
            "latitude": z_obj.latitude,
            "longitude": z_obj.longitude,
            "variables": vars_data,
        })

    # Correlated ECO Engine alerts
    eco_alerts = list(Incident.objects.filter(
        source__icontains="ECO-Engine"
    ).order_by("-detected_at")[:10].values(
        "id", "title", "severity", "incident_type", "description", "detected_at", "latitude", "longitude", "metadata"
    ))

    return JsonResponse({
        "zones": zones,
        "fires": fires,
        "stations": stations,
        "incidents": incidents,
        "anomalies": anomalies,
        "vegetation": vegetation_points,
        "atmosphere": atmo_points,
        "risks": risk_points,
        "hydrology": hydro_stations,
        "floods": floods,
        "climate_summary": climate_summary,
        "eco_alerts": eco_alerts,
    })


def zones_api(request):
    from apps.geography.models import MonitoringZone
    zones = list(MonitoringZone.objects.values(
        "id", "name", "zone_type", "current_iez", "status",
        "vulnerability_level", "latitude", "longitude", "area_km2"
    ))
    return JsonResponse({"zones": zones})


def fires_api(request):
    from apps.fires.models import FireDetection
    fires = list(FireDetection.objects.order_by("-detected_at")[:100].values())
    return JsonResponse({"fires": fires})


def stations_api(request):
    from apps.sensors.models import MonitoringStation
    stations = list(MonitoringStation.objects.values(
        "id", "code", "name", "status", "latitude", "longitude", "is_simulated"
    ))
    return JsonResponse({"stations": stations})


def incidents_api(request):
    from apps.incidents.models import Incident
    incidents = list(Incident.objects.order_by("-detected_at")[:100].values(
        "id", "title", "incident_type", "severity", "status", "detected_at",
        "latitude", "longitude", "zone_id"
    ))
    return JsonResponse({"incidents": incidents})


def alerts_api(request):
    from apps.alerts.models import Alert
    alerts = list(Alert.objects.order_by("-created_at")[:100].values(
        "id", "severity", "message", "status", "created_at", "channel"
    ))
    return JsonResponse({"alerts": alerts})


def vegetation_api(request):
    """API endpoint for vegetation data (Chart.js)."""
    from apps.vegetation.models import VegetationObservation
    from django.db.models import Avg

    # Last 30 days average NDVI by day
    from datetime import timedelta
    now = timezone.now()
    data = []
    for d in range(30):
        date = (now - timedelta(days=d)).date()
        avg = VegetationObservation.objects.filter(
            index_name="NDVI", acquisition_date=date
        ).aggregate(avg=Avg("value"))["avg"]
        data.append({
            "date": date.isoformat(),
            "ndvi": round(float(avg), 3) if avg else None,
        })
    return JsonResponse({"vegetation": list(reversed(data))})


def climate_api(request):
    """API endpoint for climate data (Chart.js)."""
    from apps.climate.models import ClimateObservation
    from django.db.models import Avg

    now = timezone.now()
    temps = []
    precip = []
    for d in range(30):
        date = (now - timedelta(days=d))
        day_start = date.replace(hour=0, minute=0, second=0)
        day_end = date.replace(hour=23, minute=59, second=59)

        t = ClimateObservation.objects.filter(
            variable="TEMPERATURE", observed_at__range=(day_start, day_end)
        ).aggregate(avg=Avg("value"))["avg"]
        p = ClimateObservation.objects.filter(
            variable="PRECIPITATION", observed_at__range=(day_start, day_end)
        ).aggregate(avg=Avg("value"))["avg"]

        temps.append({"date": day_start.date().isoformat(), "value": round(float(t), 1) if t else None})
        precip.append({"date": day_start.date().isoformat(), "value": round(float(p), 1) if p else None})

    return JsonResponse({"temperature": list(reversed(temps)), "precipitation": list(reversed(precip))})


def iez_api(request):
    """API endpoint for IEZ history (Chart.js)."""
    from apps.iez.models import IEZCalculation

    iez_list = list(IEZCalculation.objects.order_by("-calculated_at")[:50].values(
        "score", "status", "calculated_at", "zone_id"
    ))
    return JsonResponse({"iez": iez_list})


def air_quality_api(request):
    """API endpoint for air quality data (OpenAQ)."""
    from apps.atmosphere.models import AtmosphericObservation
    from django.db.models import Avg

    now = timezone.now()
    data = []
    for d in range(30):
        date = (now - timedelta(days=d)).date()
        day_start = timezone.make_aware(timezone.datetime.combine(date, timezone.datetime.min.time()))
        day_end = timezone.make_aware(timezone.datetime.combine(date, timezone.datetime.max.time()))

        for var in ["PM25", "PM10", "NO2", "O3"]:
            avg = AtmosphericObservation.objects.filter(
                variable=var, observed_at__range=(day_start, day_end)
            ).aggregate(avg=Avg("value"))["avg"]
            if avg:
                data.append({
                    "date": date.isoformat(),
                    "variable": var,
                    "value": round(float(avg), 2),
                })

    return JsonResponse({"air_quality": data})


def risk_api(request):
    """API endpoint for risk assessments."""
    from apps.risk.models import RiskAssessment

    risks = list(RiskAssessment.objects.order_by("-calculated_at")[:50].values(
        "id", "risk_type", "risk_score", "level", "severity",
        "calculated_at", "zone_id", "factors"
    ))
    return JsonResponse({"risks": risks})


def satellite_api(request):
    """API endpoint for satellite observations."""
    from apps.satellite.models import SatelliteObservation

    obs = list(SatelliteObservation.objects.order_by("-acquisition_time")[:50].values(
        "id", "satellite", "product_type", "acquisition_time",
        "cloud_cover", "source", "is_simulated", "zone_id"
    ))
    return JsonResponse({"satellite_observations": obs})


def hydrology_stations_api(request):
    """API endpoint: GET /api/hydrology/stations/"""
    from apps.water.models import HydrologicalStation, RiverForecast

    stations = []
    for s in HydrologicalStation.objects.filter(is_active=True):
        f = RiverForecast.objects.filter(station=s).order_by("-date_run", "leadtime_hours").first()
        stations.append({
            "id": s.id,
            "nom": s.nom,
            "cours_d_eau": s.cours_d_eau,
            "latitude": s.latitude,
            "longitude": s.longitude,
            "latitude_river": s.latitude_river or s.latitude,
            "longitude_river": s.longitude_river or s.longitude,
            "seuil_vigilance": s.seuil_vigilance,
            "seuil_alerte": s.seuil_alerte,
            "seuil_danger": s.seuil_danger,
            "current_discharge_m3s": f.discharge_m3s if f else 850.0,
            "trend_72h_pct": f.trend_72h_pct if f else 0.0,
            "alert_level": f.alert_level if f else "GREEN",
            "is_active": s.is_active,
        })
    return JsonResponse({"stations": stations, "count": len(stations)})


def hydrology_forecasts_api(request):
    """API endpoint: GET /api/hydrology/forecasts/ (72h hydrograms for Chart.js)"""
    from apps.water.models import HydrologicalStation, RiverForecast

    station_id = request.GET.get("station_id")
    qs = HydrologicalStation.objects.filter(is_active=True)
    if station_id:
        qs = qs.filter(id=station_id)

    forecasts_data = []
    for s in qs:
        f_list = list(RiverForecast.objects.filter(station=s).order_by("-date_run", "leadtime_hours")[:3])
        forecasts_data.append({
            "station_id": s.id,
            "station_name": s.nom,
            "cours_d_eau": s.cours_d_eau,
            "seuil_vigilance": s.seuil_vigilance,
            "seuil_alerte": s.seuil_alerte,
            "seuil_danger": s.seuil_danger,
            "series": [
                {
                    "date_run": f.date_run.isoformat(),
                    "leadtime_hours": f.leadtime_hours,
                    "discharge_m3s": f.discharge_m3s,
                    "trend_72h_pct": f.trend_72h_pct,
                    "alert_level": f.alert_level,
                }
                for f in sorted(f_list, key=lambda x: x.leadtime_hours)
            ]
        })
    return JsonResponse({"forecasts": forecasts_data})


def flood_observations_api(request):
    """API endpoint: GET /api/flood/observations/"""
    from apps.water.models import FloodObservation

    now = timezone.now()
    obs_list = list(FloodObservation.objects.order_by("-observation_date")[:20].values(
        "id", "tile_name", "observation_date", "flooded_area_km2", "flooded_pixels_count", "source", "is_simulated", "zone_id", "flood_geojson"
    ))
    total_area_km2 = sum(o["flooded_area_km2"] for o in obs_list[:2]) if obs_list else 0.0

    features = []
    for o in obs_list[:5]:
        gj = o.get("flood_geojson")
        if isinstance(gj, dict) and gj.get("features"):
            features.extend(gj["features"])

    return JsonResponse({
        "observations": obs_list,
        "total_flooded_km2": round(total_area_km2, 2),
        "total_flooded_ha": round(total_area_km2 * 100.0, 1),
        "geojson": {"type": "FeatureCollection", "features": features},
    })


def climate_summary_api(request):
    """API endpoint: GET /api/climate/summary/ (6 key weather variables per zone/commune)"""
    from apps.geography.models import MonitoringZone
    from apps.climate.models import ClimateObservation

    now = timezone.now()
    zones_data = []

    for z in MonitoringZone.objects.all():
        vars_dict = {}
        for var_code, var_key, unit_default, fallback_val in [
            ("TEMPERATURE", "temperature_c", "°C", 34.0),
            ("PRECIPITATION", "precipitation_24h_mm", "mm", 1.5),
            ("HUMIDITY", "humidity_pct", "%", 42.0),
            ("WIND_SPEED", "wind_speed_ms", "m/s", 4.5),
            ("SOLAR_RADIATION", "solar_radiation_mj", "MJ/m²", 22.0),
            ("SURFACE_PRESSURE", "surface_pressure_kpa", "kPa", 97.5),
        ]:
            val = ClimateObservation.objects.filter(
                zone=z, variable=var_code
            ).order_by("-observed_at").values_list("value", "unit").first()
            if val:
                vars_dict[var_key] = {"value": round(val[0], 1), "unit": val[1] or unit_default}
            else:
                vars_dict[var_key] = {"value": fallback_val, "unit": unit_default}

        zones_data.append({
            "zone_id": z.id,
            "zone_name": z.name,
            "latitude": z.latitude,
            "longitude": z.longitude,
            "variables": vars_dict,
        })

    return JsonResponse({"climate_summary": zones_data, "count": len(zones_data)})


def eco_engine_alerts_api(request):
    """API endpoint: GET /api/eco-engine/alerts/ (Multi-source cross-correlated alerts with AI notes)"""
    from apps.incidents.models import Incident

    alerts = list(Incident.objects.filter(
        source__icontains="ECO-Engine"
    ).order_by("-detected_at")[:50].values(
        "id", "title", "severity", "incident_type", "description",
        "detected_at", "status", "latitude", "longitude", "zone_id", "metadata"
    ))
    return JsonResponse({"alerts": alerts, "count": len(alerts)})


from django.views.decorators.csrf import csrf_exempt


@csrf_exempt
def ai_diagnose_api(request):
    """API endpoint: POST or GET /api/ai/diagnose/ (Instant GPT-OSS diagnosis for entities)"""
    import json
    from ai.groq import GroqProvider

    entity_type = request.GET.get("type") or "station"
    entity_data = {}
    if request.method == "POST":
        try:
            body = json.loads(request.body.decode("utf-8"))
            entity_type = body.get("type", entity_type)
            entity_data = body.get("data", {})
        except Exception:
            pass
    elif "data" in request.GET:
        try:
            entity_data = json.loads(request.GET.get("data"))
        except Exception:
            pass

    groq = GroqProvider()
    diagnosis = groq.diagnose_entity(entity_type, entity_data)
    groq.close()
    return JsonResponse({"status": "ok", "diagnosis": diagnosis, "model": groq.model})


@csrf_exempt
def ai_chat_api(request):
    """API endpoint: POST /api/ai/chat/ (Conversational Assistant Copilot powered by GPT-OSS)"""
    import json
    from ai.groq import GroqProvider

    query = "Quel est l'état hydrologique et environnemental du Mali aujourd'hui ?"
    context = {}
    if request.method == "POST":
        try:
            body = json.loads(request.body.decode("utf-8"))
            query = body.get("query", query)
            context = body.get("context", {})
        except Exception:
            pass
    else:
        query = request.GET.get("query", query)

    groq = GroqProvider()
    answer = groq.chat_copilot(query, context)
    groq.close()
    return JsonResponse({"status": "ok", "answer": answer, "model": groq.model})


def climate_live_api(request):
    """
    API endpoint: GET /api/climate/live/
    Returns real-time weather & 7-day precipitation forecasts from Open-Meteo.
    Cached in Redis for 20 minutes (1200 seconds).
    Accepts: ?lat=...&lon=... OR ?zone_id=... OR ?city=... (or empty for all key Mali cities).
    """
    from django.core.cache import cache
    from data_providers.open_meteo import OpenMeteoProvider
    from apps.geography.models import MonitoringZone

    lat = request.GET.get("lat") or request.GET.get("latitude")
    lon = request.GET.get("lon") or request.GET.get("longitude")
    zone_id = request.GET.get("zone_id")
    city = request.GET.get("city")

    provider = OpenMeteoProvider()

    # Resolve coordinates if zone_id or city is provided
    if zone_id:
        try:
            zone = MonitoringZone.objects.get(pk=zone_id)
            lat, lon = zone.latitude, zone.longitude
        except MonitoringZone.DoesNotExist:
            pass
    elif city and city in provider.MALI_CITIES:
        lat = provider.MALI_CITIES[city]["latitude"]
        lon = provider.MALI_CITIES[city]["longitude"]

    # Case 1: Specific Coordinate Weather
    if lat is not None and lon is not None:
        try:
            lat_f = round(float(lat), 3)
            lon_f = round(float(lon), 3)
        except (ValueError, TypeError):
            return JsonResponse({"status": "error", "message": "Coordonnées invalides"}, status=400)

        cache_key = f"live_weather_{lat_f}_{lon_f}"
        try:
            cached_result = cache.get(cache_key)
            if cached_result:
                return JsonResponse({**cached_result, "cached": True})
        except Exception:
            pass

        live_data = provider.fetch_live_weather(lat_f, lon_f)
        forecast_7d = provider.fetch_7d_forecast(lat_f, lon_f)
        provider.close()

        response_data = {
            "status": "ok",
            "latitude": lat_f,
            "longitude": lon_f,
            "current": live_data.get("current", {}),
            "hourly_24h": live_data.get("hourly_24h", []),
            "forecast_7d": forecast_7d.get("days", []),
            "total_precipitation_7d_mm": forecast_7d.get("total_precipitation_7d_mm", 0.0),
            "cached": False
        }
        # 20 minutes = 1200 seconds
        try:
            cache.set(cache_key, response_data, timeout=1200)
        except Exception:
            pass
        return JsonResponse(response_data)

    # Case 2: National Overview of All 8 Key Mali Cities
    cache_key = "live_weather_mali_cities_overview"
    try:
        cached_overview = cache.get(cache_key)
        if cached_overview:
            return JsonResponse({"status": "ok", "cities": cached_overview, "count": len(cached_overview), "cached": True})
    except Exception:
        pass

    overview = provider.fetch_mali_cities_overview()
    provider.close()

    try:
        cache.set(cache_key, overview, timeout=1200)
    except Exception:
        pass
    return JsonResponse({"status": "ok", "cities": overview, "count": len(overview), "cached": False})




