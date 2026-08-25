from django.urls import path
from . import views

app_name = "reports"

urlpatterns = [
    path("", views.report_list_view, name="report_list"),
    path("api/create/", views.api_report_create, name="api_report_create"),
    path("api/list/", views.api_report_list, name="api_report_list"),
]

