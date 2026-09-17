from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_GET
from django.db.models import Q
from .models import Region, RegionalDirectorate, MonitoringZone

@require_GET
def regions_api(request):
    """
    GET /api/geography/regions/
    Renvoie la liste des 19 régions administratives du Mali (+ District de Bamako)
    selon le découpage territorial 2023, avec leurs chefs-lieux, statistiques
    démographiques/superficies et coordonnées GPS centrales.
    """
    search = request.GET.get("search", "").strip()
    qs = Region.objects.all().prefetch_related("zones", "directorates").order_by("region_number", "name")

    if search:
        qs = qs.filter(
            Q(name__icontains=search) |
            Q(code__icontains=search) |
            Q(capital__icontains=search)
        )

    results = []
    for r in qs:
        results.append({
            "id": r.id,
            "name": r.name,
            "code": r.code,
            "region_number": r.region_number,
            "capital": r.capital,
            "latitude": r.latitude,
            "longitude": r.longitude,
            "area_km2": r.area_km2,
            "population": r.population,
            "zones_count": r.zones.count(),
            "directorates_count": r.directorates.count(),
            "directorates_types": list(
                r.directorates.filter(is_active=True).values_list("directorate_type", flat=True).distinct()
            ),
        })

    return JsonResponse({
        "count": len(results),
        "results": results,
        "regions": results,
    })

@require_GET
def directorates_api(request):
    """
    GET /api/geography/directorates/?region=<id|code>&type=<DRPC|DRH|...>&is_active=true
    Liste filtrable des directions régionales opérationnelles avec coordonnées,
    contacts téléphoniques, numéro vert d'urgence (122) et fiches détaillées.
    """
    region_param = request.GET.get("region", "").strip()
    type_param = request.GET.get("type", "").strip().upper()
    is_active_param = request.GET.get("is_active", "").strip().lower()
    search = request.GET.get("search", "").strip()

    qs = RegionalDirectorate.objects.select_related("region").prefetch_related("region__zones").all()

    if region_param:
        if region_param.isdigit():
            qs = qs.filter(region_id=int(region_param))
        else:
            qs = qs.filter(Q(region__code__iexact=region_param) | Q(region__name__icontains=region_param))

    if type_param:
        qs = qs.filter(directorate_type=type_param)

    if is_active_param in ["true", "1", "yes"]:
        qs = qs.filter(is_active=True)
    elif is_active_param in ["false", "0", "no"]:
        qs = qs.filter(is_active=False)

    if search:
        qs = qs.filter(
            Q(name__icontains=search) |
            Q(address__icontains=search) |
            Q(phone_primary__icontains=search) |
            Q(email__icontains=search) |
            Q(region__name__icontains=search)
        )

    results = []
    for d in qs:
        zones_names = list(d.region.zones.values_list("name", flat=True))
        results.append({
            "id": d.id,
            "name": d.name,
            "type": d.directorate_type,
            "directorate_type": d.directorate_type,
            "type_display": d.get_directorate_type_display(),
            "icon": d.icon_class,
            "badge_color": d.badge_color,
            "region": {
                "id": d.region.id,
                "name": d.region.name,
                "code": d.region.code,
                "region_number": d.region.region_number,
                "capital": d.region.capital,
            },
            "address": d.address,
            "latitude": d.latitude,
            "longitude": d.longitude,
            "phone_primary": d.phone_primary,
            "phone_secondary": d.phone_secondary,
            "emergency_number": d.emergency_number or "122",
            "email": d.email,
            "is_active": d.is_active,
            "notes": d.notes,
            "zones_under_jurisdiction": zones_names,
            "zones_count": len(zones_names),
        })

    return JsonResponse({
        "count": len(results),
        "results": results,
        "directorates": results,
    })

@require_GET
def directorates_by_zone_api(request, zone_id):
    """
    GET /api/geography/directorates/by-zone/<zone_id>/
    Renvoie en un seul appel les contacts d'urgence et l'ensemble des directions régionales
    compétentes pour une zone d'alerte spécifique (utile pour la fiche d'incident et l'envoi d'alertes SMS/WhatsApp).
    """
    zone = get_object_or_404(
        MonitoringZone.objects.select_related("region").prefetch_related("competent_directorates"),
        pk=zone_id
    )

    competent_qs = zone.get_competent_directorates().select_related("region")

    directorates_list = []
    emergency_contacts = {
        "national_emergency": "122",
        "drpc_phone": None,
        "drpc_emergency": "122",
        "hydrology_phone": None,
        "water_and_forests_phone": None,
        "sanitation_phone": None,
        "agriculture_phone": None,
    }

    for d in competent_qs:
        item = {
            "id": d.id,
            "name": d.name,
            "type": d.directorate_type,
            "type_display": d.get_directorate_type_display(),
            "icon": d.icon_class,
            "badge_color": d.badge_color,
            "phone_primary": d.phone_primary,
            "phone_secondary": d.phone_secondary,
            "emergency_number": d.emergency_number or "122",
            "email": d.email,
            "address": d.address,
            "latitude": d.latitude,
            "longitude": d.longitude,
        }
        directorates_list.append(item)

        if d.directorate_type == "DRPC":
            emergency_contacts["drpc_phone"] = d.phone_primary
            emergency_contacts["drpc_emergency"] = d.emergency_number or "122"
        elif d.directorate_type == "DRH":
            emergency_contacts["hydrology_phone"] = d.phone_primary
        elif d.directorate_type == "DREF":
            emergency_contacts["water_and_forests_phone"] = d.phone_primary
        elif d.directorate_type == "DRACPN":
            emergency_contacts["sanitation_phone"] = d.phone_primary
        elif d.directorate_type == "DRA":
            emergency_contacts["agriculture_phone"] = d.phone_primary

    # Active incidents in this zone
    from apps.incidents.models import Incident
    active_incidents = list(
        Incident.objects.filter(zone=zone, status__in=["NEW", "INVESTIGATING", "CONFIRMED"])
        .values("id", "title", "incident_type", "severity", "status", "detected_at")[:5]
    )

    # Pre-formatted alert payload for SMS / WhatsApp dispatch
    region_name = zone.region.name if zone.region else "Non spécifiée"
    sms_template = (
        f"🚨 [ALERTE ECO-SURVEILLANCE MALI] Zone: {zone.name} ({region_name}) | "
        f"Statut: {zone.get_status_display()} | Vulnérabilité: {zone.get_vulnerability_level_display()} | "
        f"Contact DRPC: {emergency_contacts['drpc_phone'] or '122'} | Ligne d'urgence: 122"
    )

    return JsonResponse({
        "zone": {
            "id": zone.id,
            "name": zone.name,
            "zone_type": zone.zone_type,
            "zone_type_display": zone.get_zone_type_display(),
            "status": zone.status,
            "status_display": zone.get_status_display(),
            "vulnerability_level": zone.vulnerability_level,
            "vulnerability_display": zone.get_vulnerability_level_display(),
            "current_iez": zone.current_iez,
            "latitude": zone.latitude,
            "longitude": zone.longitude,
            "area_km2": zone.area_km2,
            "population": zone.population,
        },
        "region": {
            "id": zone.region.id if zone.region else None,
            "name": region_name,
            "code": zone.region.code if zone.region else None,
            "capital": zone.region.capital if zone.region else None,
        } if zone.region else None,
        "emergency_contacts": emergency_contacts,
        "directorates": directorates_list,
        "directorates_count": len(directorates_list),
        "active_incidents": active_incidents,
        "active_incidents_count": len(active_incidents),
        "sms_dispatch_template": sms_template,
    })
