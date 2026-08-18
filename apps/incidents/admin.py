from django.contrib import admin
from .models import Incident

@admin.register(Incident)
class IncidentAdmin(admin.ModelAdmin):
    list_display = ("title", "incident_type", "zone", "severity", "status", "risk_score", "detected_at")
    list_filter = ("incident_type", "severity", "status")
    search_fields = ("title", "description")
    date_hierarchy = "detected_at"
