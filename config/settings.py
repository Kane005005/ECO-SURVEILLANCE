"""
ECO-SURVEILLANCE MALI — Django Settings
"""
import os
from pathlib import Path
from decouple import config, Csv

BASE_DIR = Path(__file__).resolve().parent.parent

# ── Security ──────────────────────────────────────────────
SECRET_KEY = config("DJANGO_SECRET_KEY", default="django-insecure-change-me-in-production")
DEBUG = config("DJANGO_DEBUG", default="1", cast=int)
ALLOWED_HOSTS = config("DJANGO_ALLOWED_HOSTS", default="*", cast=Csv())

# ── Apps ──────────────────────────────────────────────────
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Third-party
    "rest_framework",
    "corsheaders",
    # Project
    "apps.core",
    "apps.users",
    "apps.geography",
    "apps.satellite",
    "apps.fires",
    "apps.vegetation",
    "apps.water",
    "apps.climate",
    "apps.atmosphere",
    "apps.sensors",
    "apps.anomalies",
    "apps.risk",
    "apps.incidents",
    "apps.alerts",
    "apps.iez",
    "apps.ai",
    "apps.reports",
]

# ── Middleware ─────────────────────────────────────────────
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "apps.core.context_processors.site_context",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

# ── Database ──────────────────────────────────────────────
USE_SQLITE = config("USE_SQLITE", default="0", cast=int)

if USE_SQLITE:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.contrib.gis.db.backends.postgis",
            "NAME": config("DATABASE_NAME", default="eco_surveillance"),
            "USER": config("DATABASE_USER", default="eco_user"),
            "PASSWORD": config("DATABASE_PASSWORD", default="eco_password"),
            "HOST": config("DATABASE_HOST", default="localhost"),
            "PORT": config("DATABASE_PORT", default="5432"),
        }
    }

# ── Auth ──────────────────────────────────────────────────
AUTH_USER_MODEL = "users.User"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# ── Internationalization ──────────────────────────────────
LANGUAGE_CODE = "fr"
TIME_ZONE = config("DJANGO_TIME_ZONE", default="Africa/Bamako")
USE_I18N = True
USE_TZ = True

# ── Static & Media ───────────────────────────────────────
STATIC_URL = "/static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

# ── Default PK ───────────────────────────────────────────
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ── REST Framework ────────────────────────────────────────
REST_FRAMEWORK = {
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.AllowAny"],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 50,
}

# ── CORS ──────────────────────────────────────────────────
CORS_ALLOW_ALL_ORIGINS = bool(DEBUG)

# ── Redis / Celery ───────────────────────────────────────
REDIS_URL = config("REDIS_URL", default="redis://localhost:6379/0")
CELERY_BROKER_URL = config("CELERY_BROKER_URL", default=REDIS_URL)
CELERY_RESULT_BACKEND = config("CELERY_RESULT_BACKEND", default=REDIS_URL)
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = TIME_ZONE

# ── Cache (Redis) ────────────────────────────────────────
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": REDIS_URL,
        "TIMEOUT": 3600,
        "OPTIONS": {
            "db": 1,
        },
    }
}

# ── API Keys (all optional) ──────────────────────────────
# NASA FIRMS
FIRMS_MAP_KEY = config("FIRMS_MAP_KEY", default="")
FIRMS_SOURCE = config("FIRMS_SOURCE", default="VIIRS")

# NASA POWER
NASA_POWER_BASE_URL = config("NASA_POWER_BASE_URL", default="https://power.larc.nasa.gov/api/temporal")

# CHIRPS
CHIRPS_BASE_URL = config("CHIRPS_BASE_URL", default="https://data.chc.ucsb.edu/products/CHIRPS-2.0")

# Copernicus Data Space Ecosystem (Sentinel-2, Sentinel-5P)
CDSE_CLIENT_ID = config("CDSE_CLIENT_ID", default="")
CDSE_CLIENT_SECRET = config("CDSE_CLIENT_SECRET", default="")

# Legacy Copernicus keys (deprecated, use CDSE_*)
COPERNICUS_CLIENT_ID = config("COPERNICUS_CLIENT_ID", default=CDSE_CLIENT_ID)
COPERNICUS_CLIENT_SECRET = config("COPERNICUS_CLIENT_SECRET", default=CDSE_CLIENT_SECRET)

# Copernicus EWDS / GloFAS Hydrology
CDS_API_URL = config("CDS_API_URL", default="https://ewds.climate.copernicus.eu/api")
CDS_API_KEY = config("CDS_API_KEY", default="")

# NASA Earthdata / LANCE Flood NRT3
EARTHDATA_TOKEN = config("EARTHDATA_TOKEN", default="")
LANCE_FLOOD_BASE_URL = config(
    "LANCE_FLOOD_BASE_URL",
    default="https://nrt3.modaps.eosdis.nasa.gov/archive/allData/5200/VCDWD_L3_F2_NRT/Recent",
)

# Google Flood Hub (préparatoire)
FLOOD_HUB_API_KEY = config("FLOOD_HUB_API_KEY", default="")

# ERA5 (out of MVP)
ERA5_CDS_URL = config("ERA5_CDS_URL", default="https://cds.climate.copernicus.eu/api/v2")
ERA5_CDS_KEY = config("ERA5_CDS_KEY", default="")

# OpenAQ (air quality)
OPENAQ_API_KEY = config("OPENAQ_API_KEY", default="")
OPENAQ_BASE_URL = config("OPENAQ_BASE_URL", default="https://api.openaq.org/v3")

# Google Earth Engine (out of MVP)
GEE_PROJECT = config("GEE_PROJECT", default="")

# ── AI ────────────────────────────────────────────────────
AI_PROVIDER = config("AI_PROVIDER", default="openai_compat")
GROQ_API_KEY = config("GROQ_API_KEY", default="")
GROQ_MODEL = config("GROQ_MODEL", default="openai/gpt-oss-120b")
OPENAI_API_KEY = config("OPENAI_API_KEY", default="")
OPENAI_MODEL = config("OPENAI_MODEL", default="gpt-4o-mini")
OPENAI_BASE_URL = config("OPENAI_BASE_URL", default="https://api.openai.com/v1")

# ── AWS (for Landsat S3 Requester Pays) ──────────────────
AWS_ACCESS_KEY_ID = config("AWS_ACCESS_KEY_ID", default="")
AWS_SECRET_ACCESS_KEY = config("AWS_SECRET_ACCESS_KEY", default="")
AWS_REGION = config("AWS_REGION", default="us-west-2")

# ── OpenAQ (air quality) ────────────────────────────────
OPENAQ_API_KEY = config("OPENAQ_API_KEY", default="")

# ── Demo Mode ────────────────────────────────────────────
DEMO_MODE = config("DEMO_MODE", default="1", cast=int)

# ── Logging ───────────────────────────────────────────────
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {"format": "[{asctime}] {levelname} {name} {message}", "style": "{"},
    },
    "handlers": {
        "console": {"class": "logging.StreamHandler", "formatter": "verbose"},
    },
    "root": {"handlers": ["console"], "level": "INFO"},
    "loggers": {
        "django": {"handlers": ["console"], "level": "INFO", "propagate": False},
        "apps": {"handlers": ["console"], "level": "DEBUG" if DEBUG else "INFO", "propagate": False},
        "data_providers": {"handlers": ["console"], "level": "DEBUG", "propagate": False},
    },
}
