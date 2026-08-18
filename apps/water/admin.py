from django.contrib import admin
from .models import WaterBody, WaterObservation

@admin.register(WaterBody)
class WaterBodyAdmin(admin.ModelAdmin):
    list_display = ("name", "body_type", "zone", "is_simulated")
    list_filter = ("body_type", "is_simulated")

@admin.register(WaterObservation)
class WaterObservationAdmin(admin.ModelAdmin):
    list_display = ("water_body", "metric", "value", "unit", "measured_at", "source", "is_simulated")
    list_filter = ("metric", "source", "is_simulated")
    date_hierarchy = "measured_at"
