from django.contrib import admin
from .models import VegetationObservation

@admin.register(VegetationObservation)
class VegetationObservationAdmin(admin.ModelAdmin):
    list_display = ("zone", "index_name", "value", "acquisition_date", "source", "is_simulated")
    list_filter = ("index_name", "source", "is_simulated")
    date_hierarchy = "acquisition_date"
