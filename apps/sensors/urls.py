from django.urls import path
from . import views

app_name = "sensors"

urlpatterns = [
    path("", views.station_list_view, name="station_list"),
    path("<int:pk>/", views.station_detail_view, name="station_detail"),
    path("<int:pk>/simulate/", views.simulate_view, name="simulate"),
]
