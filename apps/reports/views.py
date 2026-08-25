import json
from datetime import timedelta
from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.utils import timezone
from .models import Report, FieldReport


def report_list_view(request):
    reports = Report.objects.select_related("zone").order_by("-generated_at")[:200]
    field_reports = FieldReport.objects.all().order_by("-created_at")[:50]
    return render(request, "reports/report_list.html", {"reports": reports, "field_reports": field_reports})


@csrf_exempt
@require_http_methods(["POST"])
def api_report_create(request):
    """
    POST /api/reports/create/
    Enregistre un nouveau signalement géoréférencé envoyé en JSON.
    """
    try:
        data = json.loads(request.body.decode("utf-8")) if request.body else {}
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JsonResponse({"status": "error", "message": "Format JSON invalide"}, status=400)

    # Extraction des paramètres
    lat = data.get("latitude")
    lon = data.get("longitude")
    title = (data.get("title") or "").strip()
    description = (data.get("description") or "").strip()
    report_type = data.get("report_type", "OTHER")
    severity = data.get("severity", "MEDIUM")
    author_name = (data.get("author_name") or "Anonyme").strip()
    author_phone = (data.get("author_phone") or "").strip()

    # Validations obligatoires
    if lat is None or lon is None:
        return JsonResponse({"status": "error", "message": "Les coordonnées GPS (latitude, longitude) sont obligatoires."}, status=400)

    try:
        lat_f = float(lat)
        lon_f = float(lon)
    except (ValueError, TypeError):
        return JsonResponse({"status": "error", "message": "Coordonnées GPS numériques invalides."}, status=400)

    if not (-90.0 <= lat_f <= 90.0) or not (-180.0 <= lon_f <= 180.0):
        return JsonResponse({"status": "error", "message": "Coordonnées hors limites géographiques WGS84."}, status=400)

    if not title:
        return JsonResponse({"status": "error", "message": "Le titre de l'observation est obligatoire."}, status=400)

    valid_types = [c[0] for c in FieldReport.REPORT_TYPE_CHOICES]
    if report_type not in valid_types:
        report_type = "OTHER"

    valid_severities = [s[0] for s in FieldReport.SEVERITY_CHOICES]
    if severity not in valid_severities:
        severity = "MEDIUM"

    # Création du signalement
    report = FieldReport.objects.create(
        latitude=round(lat_f, 6),
        longitude=round(lon_f, 6),
        report_type=report_type,
        severity=severity,
        title=title[:150],
        description=description,
        author_name=author_name[:100] or "Anonyme",
        author_phone=author_phone[:30],
        is_verified=False,
    )

    return JsonResponse({
        "status": "ok",
        "message": "Signalement terrain enregistré avec succès.",
        "report": report.to_geojson_feature()["properties"]
    }, status=201)


@require_http_methods(["GET"])
def api_report_list(request):
    """
    GET /api/reports/list/
    Renvoie les signalements des 30 derniers jours sous format GeoJSON FeatureCollection.
    """
    days = int(request.GET.get("days", 30))
    since = timezone.now() - timedelta(days=days)
    reports = FieldReport.objects.filter(created_at__gte=since).order_by("-created_at")

    features = [r.to_geojson_feature() for r in reports]

    return JsonResponse({
        "type": "FeatureCollection",
        "count": len(features),
        "features": features
    })

