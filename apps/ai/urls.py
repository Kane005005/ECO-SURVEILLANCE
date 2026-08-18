from django.urls import path
from . import views

app_name = "ai"

urlpatterns = [
    path("", views.ai_analysis_view, name="analysis"),
]
