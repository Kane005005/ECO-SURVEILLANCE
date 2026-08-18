from django.shortcuts import render
from .models import WaterBody, WaterObservation

def water_list_view(request):
    bodies = WaterBody.objects.select_related("zone").all()
    return render(request, "water/water_list.html", {"water_bodies": bodies})
