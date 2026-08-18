from django.contrib import admin
from .models import Alert

@admin.register(Alert)
class AlertAdmin(admin.ModelAdmin):
    list_display = ("incident", "recipient", "channel", "severity", "status", "sent_at")
    list_filter = ("channel", "severity", "status")
