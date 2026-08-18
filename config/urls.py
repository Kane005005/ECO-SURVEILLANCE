from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("apps.core.urls")),
    path("api/", include("apps.core.api_urls")),
    path("zones/", include("apps.geography.urls")),
    path("stations/", include("apps.sensors.urls")),
    path("incidents/", include("apps.incidents.urls")),
    path("alerts/", include("apps.alerts.urls")),
    path("fires/", include("apps.fires.urls")),
    path("vegetation/", include("apps.vegetation.urls")),
    path("water/", include("apps.water.urls")),
    path("climate/", include("apps.climate.urls")),
    path("atmosphere/", include("apps.atmosphere.urls")),
    path("satellite/", include("apps.satellite.urls")),
    path("anomalies/", include("apps.anomalies.urls")),
    path("risk/", include("apps.risk.urls")),
    path("iez/", include("apps.iez.urls")),
    path("reports/", include("apps.reports.urls")),
    path("ai/", include("apps.ai.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
