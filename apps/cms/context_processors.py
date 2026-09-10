from .models import SiteSettings


def cms_context(request):
    """
    Context processor injecting site_settings into all Django templates.
    """
    try:
        settings_obj = SiteSettings.get_settings()
    except Exception:
        settings_obj = None

    return {
        "site_settings": settings_obj
    }
