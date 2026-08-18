from django.shortcuts import render
from .models import AtmosphericObservation

def atmosphere_list_view(request):
    observations = AtmosphericObservation.objects.select_related("zone").order_by("-observed_at")[:200]
    return render(request, "atmosphere/atmosphere_list.html", {"observations": observations})
