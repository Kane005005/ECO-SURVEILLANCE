from django.urls import path
from . import views

app_name = "satellite"

urlpatterns = [
    path("", views.satellite_list_view, name="satellite_list"),
]
