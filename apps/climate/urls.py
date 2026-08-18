from django.urls import path
from . import views

app_name = "climate"

urlpatterns = [
    path("", views.climate_list_view, name="climate_list"),
]
