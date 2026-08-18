from django.urls import path
from . import views

app_name = "risk"

urlpatterns = [
    path("", views.risk_list_view, name="risk_list"),
]
