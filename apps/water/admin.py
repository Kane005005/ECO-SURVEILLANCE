from django.contrib import admin
from .models import WaterBody, WaterObservation, HydrologicalStation, RiverForecast, FloodObservation


@admin.register(WaterBody)
class WaterBodyAdmin(admin.ModelAdmin):
    list_display = ("name", "body_type", "zone", "is_simulated")
    list_filter = ("body_type", "is_simulated")


@admin.register(WaterObservation)
class WaterObservationAdmin(admin.ModelAdmin):
    list_display = ("water_body", "metric", "value", "unit", "measured_at", "source", "is_simulated")
    list_filter = ("metric", "source", "is_simulated")
    date_hierarchy = "measured_at"


@admin.register(HydrologicalStation)
class HydrologicalStationAdmin(admin.ModelAdmin):
    list_display = ("nom", "cours_d_eau", "latitude", "longitude", "seuil_alerte", "is_active")
    list_filter = ("cours_d_eau", "is_active")
    search_fields = ("nom", "cours_d_eau")


@admin.register(RiverForecast)
class RiverForecastAdmin(admin.ModelAdmin):
    list_display = ("station", "date_run", "leadtime_hours", "discharge_m3s", "trend_72h_pct", "alert_level", "is_simulated")
    list_filter = ("alert_level", "leadtime_hours", "is_simulated", "station")
    date_hierarchy = "date_run"


@admin.register(FloodObservation)
class FloodObservationAdmin(admin.ModelAdmin):
    list_display = ("tile_name", "observation_date", "flooded_area_km2", "flooded_pixels_count", "source", "is_simulated")
    list_filter = ("tile_name", "source", "is_simulated")
    date_hierarchy = "observation_date"

