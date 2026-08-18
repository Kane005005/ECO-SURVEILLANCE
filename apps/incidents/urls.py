from django.urls import path
from . import views

app_name = "incidents"

urlpatterns = [
    path("", views.incident_list_view, name="incident_list"),
    path("<int:pk>/", views.incident_detail_view, name="incident_detail"),
]
