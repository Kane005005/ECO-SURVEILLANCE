from django.contrib import admin
from .models import MonitoringStation, Sensor, SensorReading

@admin.register(MonitoringStation)
class MonitoringStationAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "zone", "status", "is_simulated", "battery_level", "last_seen_at")
    list_filter = ("status", "is_simulated")
    search_fields = ("code", "name")

@admin.register(Sensor)
class SensorAdmin(admin.ModelAdmin):
    list_display = ("station", "sensor_type", "code", "unit", "is_active")
    list_filter = ("sensor_type", "is_active")

@admin.register(SensorReading)
class SensorReadingAdmin(admin.ModelAdmin):
    list_display = ("sensor", "value", "recorded_at", "quality", "is_simulated")
    list_filter = ("quality", "is_simulated")
    date_hierarchy = "recorded_at"
