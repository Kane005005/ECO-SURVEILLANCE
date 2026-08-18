from django.shortcuts import render, get_object_or_404
from .models import MonitoringZone

def zone_list_view(request):
    zones = MonitoringZone.objects.select_related("region").all()
    return render(request, "geography/zone_list.html", {"zones": zones})

def zone_detail_view(request, pk):
    zone = get_object_or_404(MonitoringZone.objects.select_related("region"), pk=pk)
    return render(request, "geography/zone_detail.html", {"zone": zone})
