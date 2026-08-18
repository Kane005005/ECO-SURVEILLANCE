from django.urls import path
from . import views

app_name = "geography"

urlpatterns = [
    path("", views.zone_list_view, name="zone_list"),
    path("<int:pk>/", views.zone_detail_view, name="zone_detail"),
]
