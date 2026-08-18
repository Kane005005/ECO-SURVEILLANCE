from django.shortcuts import render
from .models import FireDetection

def fire_list_view(request):
    fires = FireDetection.objects.select_related("zone").order_by("-detected_at")[:200]
    return render(request, "fires/fire_list.html", {"fires": fires})
