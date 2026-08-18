from django.shortcuts import render
from .models import Anomaly

def anomaly_list_view(request):
    anomalies = Anomaly.objects.select_related("zone").order_by("-detected_at")[:200]
    return render(request, "anomalies/anomaly_list.html", {"anomalies": anomalies})
