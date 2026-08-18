from django.contrib import admin
from .models import Country, Region, Circle, Commune, MonitoringZone

@admin.register(Country)
class CountryAdmin(admin.ModelAdmin):
    list_display = ("name", "code")

@admin.register(Region)
class RegionAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "country", "capital")
    list_filter = ("country",)

@admin.register(Circle)
class CircleAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "region")
    list_filter = ("region",)

@admin.register(Commune)
class CommuneAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "circle", "latitude", "longitude")
    list_filter = ("circle",)

@admin.register(MonitoringZone)
class MonitoringZoneAdmin(admin.ModelAdmin):
    list_display = ("name", "zone_type", "region", "vulnerability_level", "current_iez", "status", "is_simulated")
    list_filter = ("zone_type", "status", "vulnerability_level", "is_simulated")
    search_fields = ("name",)
