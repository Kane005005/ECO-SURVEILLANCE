from django.contrib import admin
from .models import Report, FieldReport


@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = ("title", "report_type", "zone", "generated_at")
    list_filter = ("report_type",)


@admin.register(FieldReport)
class FieldReportAdmin(admin.ModelAdmin):
    list_display = ("title", "report_type", "severity", "author_name", "is_verified", "created_at")
    list_filter = ("report_type", "severity", "is_verified", "created_at")
    search_fields = ("title", "description", "author_name", "author_phone")
    list_editable = ("is_verified",)

