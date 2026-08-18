from django.shortcuts import render, get_object_or_404
from .models import Incident

def incident_list_view(request):
    incidents = Incident.objects.select_related("zone", "assigned_to").order_by("-detected_at")[:200]
    return render(request, "incidents/incident_list.html", {"incidents": incidents})

def incident_detail_view(request, pk):
    incident = get_object_or_404(Incident.objects.select_related("zone", "assigned_to", "anomaly"), pk=pk)
    return render(request, "incidents/incident_detail.html", {"incident": incident})
