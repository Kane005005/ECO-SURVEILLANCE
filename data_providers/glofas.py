"""
Copernicus GloFAS Data Provider (CEMS Global Flood Awareness System).
Fetches river discharge forecasts (24h, 48h, 72h) across Mali river basins.
Applies River Snapping algorithm to align administrative station coordinates with peak river channels.
"""
import os
import zipfile
import tempfile
import logging
from datetime import datetime, date, timedelta
from typing import Dict, Any, List, Optional
from decouple import config

from data_providers.base import BaseDataProvider, DataSourceResult, ProviderHealth

logger = logging.getLogger("data_providers")


class GloFASProvider(BaseDataProvider):
    name = "GloFAS"
    source_type = "WATER"
    is_optional = True

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.cds_url = kwargs.get("cds_url") or config(
            "CDS_API_URL", default="https://ewds.climate.copernicus.eu/api"
        )
        self.cds_key = kwargs["cds_key"] if "cds_key" in kwargs else config("CDS_API_KEY", default="")
        self.timeout = kwargs.get("timeout", 30)

    def health_check(self) -> ProviderHealth:
        if not self.cds_key:
            if self.demo_mode:
                return ProviderHealth(
                    status="ok",
                    reason="Mode démo activé (GloFAS simulé)",
                    details={"demo_mode": True},
                )
            return ProviderHealth(
                status="not_configured",
                reason="CDS_API_KEY non configuré",
                details={"cds_url": self.cds_url},
            )
        return ProviderHealth(
            status="ok",
            reason="GloFAS configuré avec clé CDS",
            details={"cds_url": self.cds_url},
        )

    def search(self, **kwargs) -> List[Dict[str, Any]]:
        target_date = kwargs.get("date") or (datetime.utcnow().date() - timedelta(days=1)).strftime("%Y-%m-%d")
        return [
            {
                "dataset": "cems-glofas-forecast",
                "system_version": "operational",
                "variable": "river_discharge_in_the_last_24_hours",
                "date": target_date,
                "leadtime_hours": ["24", "48", "72"],
                "area": [25.0, -12.5, 10.0, 4.5],  # Bounding box Mali [N, W, S, E]
                "data_format": "grib2",
                "download_format": "zip",
            }
        ]

    def _river_snap(self, ds, lat: float, lon: float, radius: float = 0.08):
        """
        River Snapping Algorithm:
        Extracts sub-grid in radius (~8 km) around coordinates and locates
        the cell corresponding to maximum mean discharge along the channel.
        """
        try:
            var_name = "dis24" if "dis24" in ds else list(ds.data_vars.keys())[0]
            # Handle latitude ordering in CDS datasets (may be descending)
            lat_min, lat_max = min(lat - radius, lat + radius), max(lat - radius, lat + radius)
            lon_min, lon_max = min(lon - radius, lon + radius), max(lon - radius, lon + radius)

            sub_grid = ds[var_name].sel(
                latitude=slice(lat_max, lat_min),
                longitude=slice(lon_min, lon_max),
            )
            if sub_grid.size == 0:
                sub_grid = ds[var_name].sel(
                    latitude=slice(lat_min, lat_max),
                    longitude=slice(lon_min, lon_max),
                )

            dim_step = "step" if "step" in sub_grid.dims else sub_grid.dims[0]
            mean_discharge = sub_grid.mean(dim=dim_step)
            max_pos = mean_discharge.argmax(dim=["latitude", "longitude"])

            snapped_lat = float(sub_grid.latitude[max_pos["latitude"].values].values)
            snapped_lon = float(sub_grid.longitude[max_pos["longitude"].values].values)

            river_cell = sub_grid.sel(latitude=snapped_lat, longitude=snapped_lon)
            values = [float(v) for v in river_cell.values.flatten()[:3]]
            while len(values) < 3:
                values.append(values[-1] if values else 100.0)

            return snapped_lat, snapped_lon, values[0], values[1], values[2]
        except Exception as e:
            logger.warning("River snapping GRIB fallback: %s", str(e))
            return lat, lon, None, None, None

    def fetch(self, **kwargs) -> List[DataSourceResult]:
        from apps.water.models import HydrologicalStation

        stations = list(HydrologicalStation.objects.filter(is_active=True))
        if not stations:
            logger.warning("No active hydrological stations found for GloFAS sync.")
            return []

        target_date_str = kwargs.get("date") or (datetime.utcnow().date() - timedelta(days=1)).strftime("%Y-%m-%d")
        run_date = datetime.strptime(target_date_str, "%Y-%m-%d").date()

        results = []
        is_live_success = False

        if self.cds_key and not self.demo_mode:
            try:
                import cdsapi
                import xarray as xr

                c = cdsapi.Client(url=self.cds_url, key=self.cds_key, quiet=True)
                with tempfile.TemporaryDirectory() as tmp_dir:
                    zip_path = os.path.join(tmp_dir, "glofas_mali.zip")
                    c.retrieve(
                        "cems-glofas-forecast",
                        {
                            "system_version": "operational",
                            "hydrological_model": "lisflood",
                            "product_type": "control_forecast",
                            "variable": "river_discharge_in_the_last_24_hours",
                            "year": str(run_date.year),
                            "month": f"{run_date.month:02d}",
                            "day": f"{run_date.day:02d}",
                            "leadtime_hour": ["24", "48", "72"],
                            "area": [25.0, -12.5, 10.0, 4.5],
                            "data_format": "grib2",
                            "download_format": "zip",
                        },
                        zip_path,
                    )

                    with zipfile.ZipFile(zip_path, "r") as zip_ref:
                        zip_ref.extractall(tmp_dir)

                    grib_files = [
                        os.path.join(tmp_dir, f)
                        for f in os.listdir(tmp_dir)
                        if f.endswith((".grib", ".grib2", ".grb"))
                    ]

                    if grib_files:
                        ds = xr.open_dataset(grib_files[0], engine="cfgrib")
                        for station in stations:
                            snapped_lat, snapped_lon, v24, v48, v72 = self._river_snap(
                                ds, station.latitude, station.longitude, radius=0.08
                            )
                            if v24 is not None:
                                station.latitude_river = snapped_lat
                                station.longitude_river = snapped_lon
                                station.save(update_fields=["latitude_river", "longitude_river"])

                                trend_72h = ((v72 - v24) / max(v24, 1.0)) * 100.0
                                for leadtime, val in [(24, v24), (48, v48), (72, v72)]:
                                    alert_level = self._compute_alert_level(val, trend_72h, station)
                                    results.append(
                                        DataSourceResult(
                                            source=self.name,
                                            data={
                                                "station_id": station.id,
                                                "station_name": station.nom,
                                                "date_run": run_date.isoformat(),
                                                "leadtime_hours": leadtime,
                                                "discharge_m3s": round(val, 2),
                                                "trend_72h_pct": round(trend_72h, 2),
                                                "alert_level": alert_level,
                                                "is_simulated": False,
                                            },
                                            fetched_at=datetime.utcnow(),
                                            is_simulated=False,
                                        )
                                    )
                        is_live_success = True
            except Exception as e:
                logger.warning("Live GloFAS CDS retrieve failed (%s), using robust simulation.", str(e))

        if not is_live_success:
            # High-fidelity realistic simulation based on station baseline and hydrological season
            simulated_data = self._generate_simulated_forecasts(stations, run_date)
            for item in simulated_data:
                results.append(
                    DataSourceResult(
                        source=self.name,
                        data=item,
                        fetched_at=datetime.utcnow(),
                        is_simulated=True,
                    )
                )

        return results

    def _compute_alert_level(self, discharge: float, trend_72h_pct: float, station) -> str:
        """Determines alert level (GREEN, YELLOW, ORANGE, RED)."""
        if discharge >= station.seuil_danger:
            return "RED"
        if discharge >= station.seuil_alerte or (discharge >= station.seuil_vigilance and trend_72h_pct >= 30.0):
            return "ORANGE"
        if discharge >= station.seuil_vigilance or trend_72h_pct >= 15.0:
            return "YELLOW"
        return "GREEN"

    def _generate_simulated_forecasts(self, stations, run_date: date) -> List[Dict[str, Any]]:
        """Generates realistic hydrometric forecasts based on stations and hydrological parameters."""
        records = []
        month = run_date.month

        # Seasonal discharge coefficient (peaks in August-October in Mali)
        seasonal_factors = {
            1: 0.35, 2: 0.25, 3: 0.15, 4: 0.10, 5: 0.15, 6: 0.30,
            7: 0.65, 8: 1.10, 9: 1.35, 10: 1.20, 11: 0.80, 12: 0.50
        }
        factor = seasonal_factors.get(month, 0.5)

        for station in stations:
            base_q = (station.seuil_vigilance * 0.75) * factor
            # Station-specific realistic modulation
            if "Mopti" in station.nom:
                base_q *= 1.25
            elif "Gao" in station.nom:
                base_q *= 1.15

            v24 = base_q * 1.02
            v48 = base_q * 1.08
            v72 = base_q * 1.16
            trend_72h = ((v72 - v24) / max(v24, 1.0)) * 100.0

            for leadtime, val in [(24, v24), (48, v48), (72, v72)]:
                alert_lvl = self._compute_alert_level(val, trend_72h, station)
                records.append({
                    "station_id": station.id,
                    "station_name": station.nom,
                    "date_run": run_date.isoformat(),
                    "leadtime_hours": leadtime,
                    "discharge_m3s": round(val, 2),
                    "trend_72h_pct": round(trend_72h, 2),
                    "alert_level": alert_lvl,
                    "is_simulated": True,
                })

        return records

    def normalize(self, raw_data: Any) -> List[Dict[str, Any]]:
        if isinstance(raw_data, DataSourceResult):
            return [raw_data.data]
        if isinstance(raw_data, list):
            res = []
            for item in raw_data:
                if isinstance(item, DataSourceResult):
                    res.append(item.data)
                elif isinstance(item, dict):
                    res.append(item)
            return res
        if isinstance(raw_data, dict):
            return [raw_data]
        return []

    def save(self, normalized_data: List[Dict[str, Any]]) -> int:
        from apps.water.models import RiverForecast, HydrologicalStation

        saved_count = 0
        for item in normalized_data:
            try:
                station_id = item.get("station_id")
                station = HydrologicalStation.objects.filter(id=station_id).first()
                if not station:
                    station = HydrologicalStation.objects.filter(nom=item.get("station_name")).first()
                if not station:
                    continue

                date_run_val = item.get("date_run")
                if isinstance(date_run_val, str):
                    date_run_val = datetime.strptime(date_run_val, "%Y-%m-%d").date()

                RiverForecast.objects.update_or_create(
                    station=station,
                    date_run=date_run_val,
                    leadtime_hours=item.get("leadtime_hours", 24),
                    defaults={
                        "discharge_m3s": item.get("discharge_m3s", 0.0),
                        "trend_72h_pct": item.get("trend_72h_pct", 0.0),
                        "alert_level": item.get("alert_level", "GREEN"),
                        "is_simulated": item.get("is_simulated", False),
                    }
                )
                saved_count += 1
            except Exception as e:
                logger.error("Error saving GloFAS forecast: %s", str(e))
        return saved_count
