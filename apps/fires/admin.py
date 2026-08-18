from django.contrib import admin
from .models import FireDetection

@admin.register(FireDetection)
class FireDetectionAdmin(admin.ModelAdmin):
    list_display = ("latitude", "longitude", "detected_at", "satellite", "confidence", "is_simulated")
    list_filter = ("satellite", "confidence", "is_simulated")
    date_hierarchy = "detected_at"
