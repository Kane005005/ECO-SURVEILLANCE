from django.shortcuts import render


def home_view(request):
    return render(request, "home.html")


def dashboard_view(request):
    return render(request, "dashboard.html")


def map_view(request):
    return render(request, "map.html")
