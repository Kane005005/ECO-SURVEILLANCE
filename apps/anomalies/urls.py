from django.urls import path
from . import views

app_name = "anomalies"

urlpatterns = [
    path("", views.anomaly_list_view, name="anomaly_list"),
]
