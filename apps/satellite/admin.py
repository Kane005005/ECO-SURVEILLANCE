from django.contrib import admin
from .models import SatelliteObservation

@admin.register(SatelliteObservation)
class SatelliteObservationAdmin(admin.ModelAdmin):
    list_display = ("zone", "satellite", "product_type", "acquisition_time", "cloud_cover", "is_simulated")
    list_filter = ("satellite", "product_type", "is_simulated")
    date_hierarchy = "acquisition_time"
