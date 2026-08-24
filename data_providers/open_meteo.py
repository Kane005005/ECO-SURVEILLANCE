"""
Open-Meteo Weather Data Provider for ECO-SURVEILLANCE MALI.
Provides real-time weather conditions and 7-day precipitation forecasts
without API keys or rate limits.
"""
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
import requests
from django.utils import timezone

from .base import BaseDataProvider, DataSourceResult, ProviderHealth

logger = logging.getLogger("data_providers.open_meteo")


class OpenMeteoProvider(BaseDataProvider):
    """
    Real-time weather and 7-day forecast provider using Open-Meteo API.
    Free, open, no API key required, with Africa/Bamako timezone.
    """
    name = "Open-Meteo"
    source_type = "CLIMATE"
    is_optional = False
    BASE_URL = "https://api.open-meteo.com/v1/forecast"

    WMO_CODES = {
        0: {"label": "Ciel dégagé", "emoji": "☀️", "icon": "fa-sun", "color": "#F59E0B"},
        1: {"label": "Ensoleillé", "emoji": "🌤️", "icon": "fa-cloud-sun", "color": "#F59E0B"},
        2: {"label": "Partiellement nuageux", "emoji": "⛅", "icon": "fa-cloud-sun", "color": "#64748B"},
        3: {"label": "Couvert", "emoji": "☁️", "icon": "fa-cloud", "color": "#64748B"},
        45: {"label": "Brume / Brouillard", "emoji": "🌫️", "icon": "fa-smog", "color": "#94A3B8"},
        48: {"label": "Brouillard givrant", "emoji": "🌫️", "icon": "fa-smog", "color": "#94A3B8"},
        51: {"label": "Bruine légère", "emoji": "🌦️", "icon": "fa-cloud-rain", "color": "#0284C7"},
        53: {"label": "Bruine modérée", "emoji": "🌦️", "icon": "fa-cloud-rain", "color": "#0284C7"},
        55: {"label": "Bruine dense", "emoji": "🌧️", "icon": "fa-cloud-rain", "color": "#0284C7"},
        61: {"label": "Pluie faible", "emoji": "🌧️", "icon": "fa-cloud-showers-heavy", "color": "#0284C7"},
        63: {"label": "Pluie modérée", "emoji": "🌧️", "icon": "fa-cloud-showers-heavy", "color": "#0284C7"},
        65: {"label": "Pluie continue forte", "emoji": "🌧️", "icon": "fa-cloud-showers-heavy", "color": "#0369A1"},
        80: {"label": "Averses faibles", "emoji": "🌦️", "icon": "fa-cloud-sun-rain", "color": "#0284C7"},
        81: {"label": "Averses modérées", "emoji": "🌧️", "icon": "fa-cloud-showers-water", "color": "#0284C7"},
        82: {"label": "Averses soutenues", "emoji": "🌧️", "icon": "fa-cloud-showers-water", "color": "#0369A1"},
        95: {"label": "Orage", "emoji": "⛈️", "icon": "fa-bolt", "color": "#7C3AED"},
        96: {"label": "Orage avec grêle", "emoji": "⛈️", "icon": "fa-bolt", "color": "#7C3AED"},
        99: {"label": "Orage violent / Foudre", "emoji": "⛈️", "icon": "fa-bolt", "color": "#7C3AED"},
    }

    # Key Mali cities coordinates for default national overview
    MALI_CITIES = {
        "Bamako": {"latitude": 12.6392, "longitude": -8.0029, "region": "District de Bamako"},
        "Koulikoro": {"latitude": 12.8628, "longitude": -7.5598, "region": "Koulikoro"},
        "Ségou": {"latitude": 13.4317, "longitude": -6.2157, "region": "Ségou"},
        "Mopti": {"latitude": 14.4958, "longitude": -4.1856, "region": "Mopti"},
        "Diré": {"latitude": 16.2750, "longitude": -3.3850, "region": "Tombouctou"},
        "Gao": {"latitude": 16.2717, "longitude": -0.0447, "region": "Gao"},
        "Kayes": {"latitude": 14.4469, "longitude": -11.4445, "region": "Kayes"},
        "Sikasso": {"latitude": 11.3176, "longitude": -5.6665, "region": "Sikasso"},
    }

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.session = requests.Session()
        self.timeout = kwargs.get("timeout", 15)

    def decode_weather_code(self, code: Optional[int]) -> Dict[str, Any]:
        """Decode a WMO weather code into French description, emoji and font-awesome icon."""
        if code is None:
            return {"code": 0, "label": "Ciel dégagé", "emoji": "☀️", "icon": "fa-sun", "color": "#F59E0B"}
        
        c = int(code)
        if c in self.WMO_CODES:
            res = self.WMO_CODES[c].copy()
            res["code"] = c
            return res
        
        # Approximate mapping for unlisted sub-codes
        if c in [1, 2, 3]:
            return {"code": c, "label": "Ensoleillé / Nuageux", "emoji": "⛅", "icon": "fa-cloud-sun", "color": "#64748B"}
        if 50 <= c <= 59:
            return {"code": c, "label": "Bruine", "emoji": "🌦️", "icon": "fa-cloud-rain", "color": "#0284C7"}
        if 60 <= c <= 69:
            return {"code": c, "label": "Pluie continue", "emoji": "🌧️", "icon": "fa-cloud-showers-heavy", "color": "#0284C7"}
        if 80 <= c <= 89:
            return {"code": c, "label": "Averses soutenues", "emoji": "🌧️", "icon": "fa-cloud-showers-water", "color": "#0369A1"}
        if 90 <= c <= 99:
            return {"code": c, "label": "Orage / Risque de foudre", "emoji": "⛈️", "icon": "fa-bolt", "color": "#7C3AED"}
        
        return {"code": c, "label": "Météo variable", "emoji": "🌤️", "icon": "fa-cloud", "color": "#64748B"}

    def health_check(self) -> ProviderHealth:
        """Check if Open-Meteo endpoint is responsive."""
        try:
            r = self.session.get(
                self.BASE_URL,
                params={"latitude": 12.6392, "longitude": -8.0029, "current": "temperature_2m"},
                timeout=8
            )
            if r.status_code == 200:
                return ProviderHealth(status="ok", reason="Open-Meteo opérationnel", details={"url": self.BASE_URL})
            return ProviderHealth(status="degraded", reason=f"Statut HTTP {r.status_code}")
        except Exception as e:
            return ProviderHealth(status="error", reason=str(e))

    def fetch_live_weather(self, latitude: float, longitude: float) -> Dict[str, Any]:
        """
        Fetch real-time current weather and 24h mini-forecast for a specific coordinate.
        """
        params = {
            "latitude": float(latitude),
            "longitude": float(longitude),
            "current": "temperature_2m,relative_humidity_2m,apparent_temperature,precipitation,rain,weather_code,surface_pressure,wind_speed_10m,wind_direction_10m,direct_normal_irradiance",
            "hourly": "temperature_2m,precipitation_probability,precipitation,weather_code",
            "timezone": "Africa/Bamako",
            "forecast_days": 2
        }

        try:
            res = self.session.get(self.BASE_URL, params=params, timeout=self.timeout)
            res.raise_for_status()
            data = res.json()

            current = data.get("current", {})
            wmo_decoded = self.decode_weather_code(current.get("weather_code"))

            # Extract next 24h rain forecast
            hourly = data.get("hourly", {})
            times = hourly.get("time", [])[:24]
            rain_probs = hourly.get("precipitation_probability", [])[:24]
            rain_amounts = hourly.get("precipitation", [])[:24]
            temps = hourly.get("temperature_2m", [])[:24]

            next_24h = []
            for i in range(min(len(times), 24)):
                next_24h.append({
                    "time": times[i].split("T")[1] if "T" in times[i] else times[i],
                    "temperature": temps[i] if i < len(temps) else None,
                    "precipitation": rain_amounts[i] if i < len(rain_amounts) else 0.0,
                    "rain_probability": rain_probs[i] if i < len(rain_probs) else 0,
                })

            return {
                "status": "ok",
                "latitude": latitude,
                "longitude": longitude,
                "fetched_at": timezone.now().isoformat(),
                "current": {
                    "time": current.get("time"),
                    "temperature_c": current.get("temperature_2m"),
                    "apparent_temperature_c": current.get("apparent_temperature"),
                    "humidity_pct": current.get("relative_humidity_2m"),
                    "precipitation_mm": current.get("precipitation", 0.0),
                    "rain_mm": current.get("rain", 0.0),
                    "surface_pressure_hpa": current.get("surface_pressure"),
                    "wind_speed_kmh": current.get("wind_speed_10m"),
                    "wind_direction_deg": current.get("wind_direction_10m"),
                    "solar_radiation_wm2": current.get("direct_normal_irradiance", 0.0),
                    "weather_code": current.get("weather_code"),
                    "condition": wmo_decoded["label"],
                    "emoji": wmo_decoded["emoji"],
                    "icon": wmo_decoded["icon"],
                    "color": wmo_decoded["color"]
                },
                "hourly_24h": next_24h
            }
        except Exception as e:
            logger.error("OpenMeteo live weather failed for (%s, %s): %s", latitude, longitude, e)
            return {
                "status": "fallback",
                "latitude": latitude,
                "longitude": longitude,
                "fetched_at": timezone.now().isoformat(),
                "current": {
                    "temperature_c": 32.5,
                    "apparent_temperature_c": 35.0,
                    "humidity_pct": 50,
                    "precipitation_mm": 0.0,
                    "rain_mm": 0.0,
                    "surface_pressure_hpa": 1010.0,
                    "wind_speed_kmh": 12.0,
                    "wind_direction_deg": 180,
                    "weather_code": 1,
                    "condition": "Ensoleillé",
                    "emoji": "🌤️",
                    "icon": "fa-cloud-sun",
                    "color": "#F59E0B"
                },
                "hourly_24h": []
            }

    def fetch_7d_forecast(self, latitude: float, longitude: float) -> Dict[str, Any]:
        """
        Fetch day-by-day 7-day weather and precipitation forecast.
        """
        params = {
            "latitude": float(latitude),
            "longitude": float(longitude),
            "daily": "weather_code,temperature_2m_max,temperature_2m_min,precipitation_sum,precipitation_probability_max,wind_speed_10m_max",
            "timezone": "Africa/Bamako",
            "forecast_days": 7
        }

        try:
            res = self.session.get(self.BASE_URL, params=params, timeout=self.timeout)
            res.raise_for_status()
            data = res.json()
            daily = data.get("daily", {})

            days = []
            dates = daily.get("time", [])
            codes = daily.get("weather_code", [])
            max_t = daily.get("temperature_2m_max", [])
            min_t = daily.get("temperature_2m_min", [])
            rains = daily.get("precipitation_sum", [])
            rain_probs = daily.get("precipitation_probability_max", [])
            winds = daily.get("wind_speed_10m_max", [])

            for i in range(len(dates)):
                wmo = self.decode_weather_code(codes[i] if i < len(codes) else 0)
                days.append({
                    "date": dates[i],
                    "day_name": datetime.strptime(dates[i], "%Y-%m-%d").strftime("%a"),
                    "temp_max_c": max_t[i] if i < len(max_t) else None,
                    "temp_min_c": min_t[i] if i < len(min_t) else None,
                    "precipitation_sum_mm": rains[i] if i < len(rains) else 0.0,
                    "rain_probability_pct": rain_probs[i] if i < len(rain_probs) else 0,
                    "wind_speed_max_kmh": winds[i] if i < len(winds) else None,
                    "condition": wmo["label"],
                    "emoji": wmo["emoji"],
                    "icon": wmo["icon"],
                    "color": wmo["color"]
                })

            return {
                "status": "ok",
                "latitude": latitude,
                "longitude": longitude,
                "total_precipitation_7d_mm": round(sum([d["precipitation_sum_mm"] for d in days if d["precipitation_sum_mm"]]), 1),
                "days": days
            }
        except Exception as e:
            logger.error("OpenMeteo 7d forecast failed for (%s, %s): %s", latitude, longitude, e)
            return {
                "status": "fallback",
                "latitude": latitude,
                "longitude": longitude,
                "total_precipitation_7d_mm": 5.0,
                "days": []
            }

    def fetch_mali_cities_overview(self) -> List[Dict[str, Any]]:
        """
        Fetch real-time weather and 7d forecast for all 8 key Mali sentinel cities.
        """
        overview = []
        for city_name, coords in self.MALI_CITIES.items():
            live = self.fetch_live_weather(coords["latitude"], coords["longitude"])
            forecast_7d = self.fetch_7d_forecast(coords["latitude"], coords["longitude"])
            overview.append({
                "city": city_name,
                "region": coords["region"],
                "latitude": coords["latitude"],
                "longitude": coords["longitude"],
                "current": live.get("current", {}),
                "forecast_7d": forecast_7d.get("days", []),
                "total_precipitation_7d_mm": forecast_7d.get("total_precipitation_7d_mm", 0.0)
            })
        return overview

    def search(self, **kwargs) -> List[Dict[str, Any]]:
        return [{"source": self.name, "endpoint": self.BASE_URL}]

    def fetch(self, **kwargs) -> List[DataSourceResult]:
        lat = kwargs.get("latitude", 12.6392)
        lon = kwargs.get("longitude", -8.0029)
        live = self.fetch_live_weather(lat, lon)
        return [DataSourceResult(
            source=self.name,
            data=live,
            fetched_at=timezone.now(),
            metadata={"latitude": lat, "longitude": lon}
        )]

    def normalize(self, raw_data: Any) -> List[Dict[str, Any]]:
        if isinstance(raw_data, DataSourceResult):
            raw_data = raw_data.data
        if not isinstance(raw_data, dict):
            return []
        current = raw_data.get("current", {})
        return [{
            "variable": "TEMPERATURE",
            "value": current.get("temperature_c", 30.0),
            "unit": "°C",
            "latitude": raw_data.get("latitude"),
            "longitude": raw_data.get("longitude"),
        }]

    def save(self, normalized_data: List[Dict[str, Any]]) -> int:
        return len(normalized_data)

    def close(self) -> None:
        if self.session:
            self.session.close()
