from django.urls import path
from . import views

app_name = "alerts"

urlpatterns = [
    path("", views.alert_list_view, name="alert_list"),
]
