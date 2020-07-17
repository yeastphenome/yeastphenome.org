from django.contrib.sites.shortcuts import get_current_site
from yeastphenome import settings

def globals(request):
    """Returns a dict of defaults to be used by templates, if configured
    correcty in the settings.py file."""
    return {'SITE_NAME':get_current_site(request).name,
            'GOOGLE_ANALYTICS_ID': settings.GOOGLE_ANALYTICS_ID,
            'GOOGLE_ANALYTICS_SITE': settings.GOOGLE_ANALYTICS_SITE}
