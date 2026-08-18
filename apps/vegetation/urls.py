from django.urls import path
from . import views

app_name = "vegetation"

urlpatterns = [
    path("", views.vegetation_list_view, name="vegetation_list"),
]
