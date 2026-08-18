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

    return JsonResponse({
        "zones": zones,
        "active_fires": active_fires,
        "active_incidents": active_incidents,
        "unread_alerts": unread_alerts,
        "active_stations": active_stations,
        "recent_anomalies": recent_anomalies,
        "national_iez": national_iez,
    })


def map_api(request):
    from apps.geography.models import MonitoringZone
    from apps.fires.models import FireDetection
    from apps.sensors.models import MonitoringStation
    from apps.incidents.models import Incident
    from datetime import timedelta
    from django.utils import timezone

    now = timezone.now()
    week_ago = now - timedelta(days=7)

    zones = list(MonitoringZone.objects.values("id", "name", "zone_type", "current_iez", "status"))
    fires = list(FireDetection.objects.filter(detected_at__gte=week_ago).values("id", "latitude", "longitude", "confidence", "brightness"))
    stations = list(MonitoringStation.objects.values("id", "code", "name", "status", "location"))
    incidents = list(Incident.objects.exclude(status__in=["RESOLVED", "DISMISSED"]).values("id", "title", "severity", "location"))

    return JsonResponse({"zones": zones, "fires": fires, "stations": stations, "incidents": incidents})


def zones_api(request):
    from apps.geography.models import MonitoringZone
    zones = list(MonitoringZone.objects.values("id", "name", "zone_type", "current_iez", "status", "vulnerability_level"))
    return JsonResponse({"zones": zones})


def fires_api(request):
    from apps.fires.models import FireDetection
    fires = list(FireDetection.objects.order_by("-detected_at")[:100].values())
    return JsonResponse({"fires": fires})


def stations_api(request):
    from apps.sensors.models import MonitoringStation
    stations = list(MonitoringStation.objects.values("id", "code", "name", "status", "is_simulated"))
    return JsonResponse({"stations": stations})


def incidents_api(request):
    from apps.incidents.models import Incident
    incidents = list(Incident.objects.order_by("-detected_at")[:100].values("id", "title", "type", "severity", "status", "detected_at"))
    return JsonResponse({"incidents": incidents})


def alerts_api(request):
    from apps.alerts.models import Alert
    alerts = list(Alert.objects.order_by("-sent_at")[:100].values("id", "severity", "message", "status", "sent_at"))
    return JsonResponse({"alerts": alerts})
