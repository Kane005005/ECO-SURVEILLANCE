from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.http import JsonResponse
from .models import MonitoringStation, Sensor, SensorReading
from .services import SensorSimulator

def station_list_view(request):
    stations = MonitoringStation.objects.select_related("zone").all()
    return render(request, "sensors/station_list.html", {"stations": stations})

def station_detail_view(request, pk):
    station = get_object_or_404(MonitoringStation.objects.select_related("zone"), pk=pk)
    sensors = Sensor.objects.filter(station=station)
    readings = SensorReading.objects.filter(sensor__station=station).select_related("sensor").order_by("-recorded_at")[:100]
    return render(request, "sensors/station_detail.html", {
        "station": station, "sensors": sensors, "readings": readings,
    })

def simulate_view(request, pk):
    station = get_object_or_404(MonitoringStation, pk=pk)
    scenario = request.POST.get("scenario", SensorSimulator.SCENARIO_NORMAL)
    simulator = SensorSimulator()
    readings = simulator.generate_readings(station, scenario)
    messages.success(request, f"{len(readings)} mesures générées pour {station.code} (scénario: {scenario})")
    return redirect("sensors:station_detail", pk=pk)
