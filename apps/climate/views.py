from django.shortcuts import render
from .models import ClimateObservation

def climate_list_view(request):
    observations = ClimateObservation.objects.select_related("zone").order_by("-observed_at")[:200]
    return render(request, "climate/climate_list.html", {"observations": observations})
