from django.shortcuts import render
from .models import IEZCalculation

def iez_list_view(request):
    calculations = IEZCalculation.objects.select_related("zone").order_by("-calculated_at")[:200]
    return render(request, "iez/iez_list.html", {"calculations": calculations})
