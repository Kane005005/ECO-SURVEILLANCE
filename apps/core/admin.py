from django.contrib import admin
from .models import DataSource


@admin.register(DataSource)
class DataSourceAdmin(admin.ModelAdmin):
    list_display = ("name", "provider", "source_type", "status", "is_active", "is_simulated", "last_sync")
    list_filter = ("source_type", "status", "is_active", "is_simulated")
    search_fields = ("name", "provider")
