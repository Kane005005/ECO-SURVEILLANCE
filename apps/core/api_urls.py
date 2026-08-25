from django.urls import path
from . import api_views
from apps.incidents.views import incident_analyze_api
from apps.reports.views import api_report_create, api_report_list

app_name = "api"

urlpatterns = [
    path("dashboard/", api_views.dashboard_api, name="dashboard"),
    path("map/", api_views.map_api, name="map"),
    path("zones/", api_views.zones_api, name="zones"),
    path("fires/", api_views.fires_api, name="fires"),
    path("stations/", api_views.stations_api, name="stations"),
    path("incidents/", api_views.incidents_api, name="incidents"),
    path("incidents/<int:pk>/analyze/", incident_analyze_api, name="incident_analyze"),
    path("alerts/", api_views.alerts_api, name="alerts"),
    path("vegetation/", api_views.vegetation_api, name="vegetation"),
    path("climate/", api_views.climate_api, name="climate"),
    path("iez/", api_views.iez_api, name="iez"),
    path("air-quality/", api_views.air_quality_api, name="air_quality"),
    path("risk/", api_views.risk_api, name="risk"),
    path("satellite/", api_views.satellite_api, name="satellite"),
    # New Hydrology, Flood, Climate & ECO-Engine endpoints
    path("hydrology/stations/", api_views.hydrology_stations_api, name="hydrology_stations"),
    path("hydrology/forecasts/", api_views.hydrology_forecasts_api, name="hydrology_forecasts"),
    path("flood/observations/", api_views.flood_observations_api, name="flood_observations"),
    path("climate/summary/", api_views.climate_summary_api, name="climate_summary"),
    path("climate/live/", api_views.climate_live_api, name="climate_live"),
    path("eco-engine/alerts/", api_views.eco_engine_alerts_api, name="eco_engine_alerts"),
    path("ai/diagnose/", api_views.ai_diagnose_api, name="ai_diagnose"),
    path("ai/chat/", api_views.ai_chat_api, name="ai_chat"),
    # Field Reports / Crowdsourcing
    path("reports/create/", api_report_create, name="report_create"),
    path("reports/list/", api_report_list, name="report_list"),
]

