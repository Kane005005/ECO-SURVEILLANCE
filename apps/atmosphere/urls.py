from django.urls import path
from . import views

app_name = "atmosphere"

urlpatterns = [
    path("", views.atmosphere_list_view, name="atmosphere_list"),
]
