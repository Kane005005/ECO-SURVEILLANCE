from django.urls import path
from . import views

app_name = "iez"

urlpatterns = [
    path("", views.iez_list_view, name="iez_list"),
]
