from django.shortcuts import render
from .models import Report

def report_list_view(request):
    reports = Report.objects.select_related("zone").order_by("-generated_at")[:200]
    return render(request, "reports/report_list.html", {"reports": reports})
