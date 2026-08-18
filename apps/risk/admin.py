from django.contrib import admin
from .models import RiskAssessment

@admin.register(RiskAssessment)
class RiskAssessmentAdmin(admin.ModelAdmin):
    list_display = ("zone", "risk_type", "risk_score", "confidence_score", "level", "severity", "calculated_at", "is_simulated")
    list_filter = ("risk_type", "level", "severity", "is_simulated")
    date_hierarchy = "calculated_at"
