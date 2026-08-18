from django.contrib import admin
from .models import ClimateObservation

@admin.register(ClimateObservation)
class ClimateObservationAdmin(admin.ModelAdmin):
    list_display = ("zone", "variable", "value", "unit", "observed_at", "source", "is_simulated")
    list_filter = ("variable", "source", "is_simulated")
    date_hierarchy = "observed_at"
