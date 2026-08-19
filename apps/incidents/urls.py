from django.urls import path
from . import views

app_name = "incidents"

urlpatterns = [
    path("", views.incident_list_view, name="incident_list"),
    path("<int:pk>/", views.incident_detail_view, name="incident_detail"),
    path("<int:pk>/analyze/", views.incident_analyze_api, name="incident_analyze"),
    path("<int:pk>/update-status/", views.incident_update_status_view, name="incident_update_status"),
]
