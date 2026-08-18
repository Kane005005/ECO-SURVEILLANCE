from django.conf import settings


def site_context(request):
    return {
        "DEMO_MODE": getattr(settings, "DEMO_MODE", False),
        "SITE_NAME": "ECO-SURVEILLANCE MALI",
    }
