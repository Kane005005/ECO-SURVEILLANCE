from django.shortcuts import render
from .models import VegetationObservation

def vegetation_list_view(request):
    observations = VegetationObservation.objects.select_related("zone").order_by("-acquisition_date")[:200]
    return render(request, "vegetation/vegetation_list.html", {"observations": observations})
