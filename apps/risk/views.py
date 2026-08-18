from django.shortcuts import render
from .models import RiskAssessment

def risk_list_view(request):
    assessments = RiskAssessment.objects.select_related("zone").order_by("-calculated_at")[:200]
    return render(request, "risk/risk_list.html", {"assessments": assessments})
