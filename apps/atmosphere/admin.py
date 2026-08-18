from django.contrib import admin
from .models import AtmosphericObservation

@admin.register(AtmosphericObservation)
class AtmosphericObservationAdmin(admin.ModelAdmin):
    list_display = ("zone", "variable", "value", "unit", "observed_at", "source", "quality_flag", "is_simulated")
    list_filter = ("variable", "source", "quality_flag", "is_simulated")
    date_hierarchy = "observed_at"
