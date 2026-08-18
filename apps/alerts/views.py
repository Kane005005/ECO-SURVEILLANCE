from django.shortcuts import render
from .models import Alert

def alert_list_view(request):
    alerts = Alert.objects.select_related("incident", "recipient").order_by("-created_at")[:200]
    return render(request, "alerts/alert_list.html", {"alerts": alerts})
