"""
Data providers for ECO-SURVEILLANCE MALI.
Each provider handles one external data source.
"""
from .base import BaseDataProvider, DataSourceResult, ProviderHealth
from .firms import FIRMSProvider
from .nasa_power import NASAPowerProvider
from .chirps import CHIRPSProvider
from .sentinel2 import Sentinel2Provider
from .sentinel5p import Sentinel5PProvider
from .landsat import LandsatProvider
from .openaq import OpenAQProvider
from .glofas import GloFASProvider
from .lance_flood import LANCEFloodProvider
from .flood_hub import FloodHubProvider
from .open_meteo import OpenMeteoProvider

__all__ = [
    "BaseDataProvider",
    "DataSourceResult",
    "ProviderHealth",
    "FIRMSProvider",
    "NASAPowerProvider",
    "CHIRPSProvider",
    "Sentinel2Provider",
    "Sentinel5PProvider",
    "LandsatProvider",
    "OpenAQProvider",
    "GloFASProvider",
    "LANCEFloodProvider",
    "FloodHubProvider",
    "OpenMeteoProvider",
]
