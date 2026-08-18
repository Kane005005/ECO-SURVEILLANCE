from django.urls import path
from . import views

app_name = "fires"

urlpatterns = [
    path("", views.fire_list_view, name="fire_list"),
]
