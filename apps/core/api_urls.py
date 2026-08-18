from django.urls import path
from . import api_views

app_name = "api"

urlpatterns = [
    path("dashboard/", api_views.dashboard_api, name="dashboard"),
    path("map/", api_views.map_api, name="map"),
    path("zones/", api_views.zones_api, name="zones"),
    path("fires/", api_views.fires_api, name="fires"),
    path("stations/", api_views.stations_api, name="stations"),
    path("incidents/", api_views.incidents_api, name="incidents"),
    path("alerts/", api_views.alerts_api, name="alerts"),
]
