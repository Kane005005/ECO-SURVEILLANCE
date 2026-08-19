from django.http import JsonResponse
from django.db.models import Count, Q
from django.utils import timezone
from datetime import timedelta


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
    })


def map_api(request):
    from apps.geography.models import MonitoringZone
    from apps.fires.models import FireDetection
    from apps.sensors.models import MonitoringStation
    from apps.incidents.models import Incident
    from apps.anomalies.models import Anomaly

    now = timezone.now()
    week_ago = now - timedelta(days=7)

    zones = list(MonitoringZone.objects.values(
        "id", "name", "zone_type", "current_iez", "status",
        "latitude", "longitude", "vulnerability_level"
    ))
    fires = list(FireDetection.objects.filter(detected_at__gte=week_ago).values(
        "id", "latitude", "longitude", "confidence", "brightness", "frp", "detected_at"
    ))
    stations = list(MonitoringStation.objects.values(
        "id", "code", "name", "status", "latitude", "longitude", "is_simulated"
    ))
    incidents = list(Incident.objects.exclude(status__in=["RESOLVED", "DISMISSED"]).values(
        "id", "title", "severity", "latitude", "longitude", "incident_type", "detected_at"
    ))

    # Anomalies for map
    anomalies = list(Anomaly.objects.filter(
        detected_at__gte=week_ago
    ).values("id", "anomaly_type", "severity", "zone_id", "detected_at")[:50])

    return JsonResponse({
        "zones": zones,
        "fires": fires,
        "stations": stations,
        "incidents": incidents,
        "anomalies": anomalies,
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
