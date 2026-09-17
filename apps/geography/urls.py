from django.urls import path
from . import views, api_views

app_name = "geography"

urlpatterns = [
    # Template views
    path("", views.zone_list_view, name="zone_list"),
    path("<int:pk>/", views.zone_detail_view, name="zone_detail"),

    # REST API endpoints
    path("regions/", api_views.regions_api, name="regions_api"),
    path("directorates/", api_views.directorates_api, name="directorates_api"),
    path("directorates/by-zone/<int:zone_id>/", api_views.directorates_by_zone_api, name="directorates_by_zone_api"),
]
