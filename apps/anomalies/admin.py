from django.contrib import admin
from .models import Anomaly

@admin.register(Anomaly)
class AnomalyAdmin(admin.ModelAdmin):
    list_display = ("anomaly_type", "zone", "severity", "score", "confidence", "status", "detected_at", "is_simulated")
    list_filter = ("anomaly_type", "severity", "status", "is_simulated")
    search_fields = ("zone__name", "metric")
    date_hierarchy = "detected_at"
