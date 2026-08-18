from django.contrib import admin
from .models import IEZCalculation

@admin.register(IEZCalculation)
class IEZCalculationAdmin(admin.ModelAdmin):
    list_display = ("zone", "score", "status", "algorithm_version", "calculated_at", "is_simulated")
    list_filter = ("status", "is_simulated")
    date_hierarchy = "calculated_at"
