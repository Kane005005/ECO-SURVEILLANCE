from django.shortcuts import render
from .models import SatelliteObservation

def satellite_list_view(request):
    observations = SatelliteObservation.objects.select_related("zone").order_by("-acquisition_time")[:200]
    return render(request, "satellite/satellite_list.html", {"observations": observations})
