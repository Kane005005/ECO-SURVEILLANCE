from django.contrib import admin
from .models import Country, Region, Circle, Commune, MonitoringZone, RegionalDirectorate

@admin.register(Country)
class CountryAdmin(admin.ModelAdmin):
    list_display = ("name", "code")

class RegionalDirectorateInline(admin.TabularInline):
    model = RegionalDirectorate
    extra = 1
    fields = ("directorate_type", "name", "phone_primary", "emergency_number", "is_active")

@admin.register(Region)
class RegionAdmin(admin.ModelAdmin):
    list_display = ("region_number", "name", "code", "capital", "latitude", "longitude", "area_km2", "population")
    list_display_links = ("name",)
    list_filter = ("country",)
    search_fields = ("name", "code", "capital")
    inlines = [RegionalDirectorateInline]

@admin.register(RegionalDirectorate)
class RegionalDirectorateAdmin(admin.ModelAdmin):
    list_display = ("name", "directorate_type", "region", "phone_primary", "emergency_number", "is_active")
    list_filter = ("directorate_type", "region", "is_active")
    search_fields = ("name", "region__name", "phone_primary", "email")
    fieldsets = (
        ("Identification", {
            "fields": ("region", "directorate_type", "name", "is_active")
        }),
        ("Localisation Siège", {
            "fields": ("address", "latitude", "longitude")
        }),
        ("Coordonnées & Alertes d'Urgence", {
            "fields": ("phone_primary", "phone_secondary", "emergency_number", "email")
        }),
        ("Notes & Compléments", {
            "fields": ("notes",)
        }),
    )

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
    filter_horizontal = ("competent_directorates",)
