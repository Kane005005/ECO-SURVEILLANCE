from django.contrib import admin
from .models import AIAnalysis

@admin.register(AIAnalysis)
class AIAnalysisAdmin(admin.ModelAdmin):
    list_display = ("provider", "model", "incident", "created_at")
    list_filter = ("provider", "model")
