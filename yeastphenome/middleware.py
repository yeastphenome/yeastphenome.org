from django.http import HttpResponseForbidden
from django.conf import settings
from django.shortcuts import redirect
from django.urls import reverse


class MaintenanceModeMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Check if maintenance mode is enabled in settings
        if getattr(settings, 'MAINTENANCE_MODE', False):
            # Define URLs that should remain accessible
            excluded_urls = [
                reverse('common:support'),
                reverse('common:project'),
                reverse('common:faq'),
                reverse('common:contributors'),
                reverse('common:maintenance'),
                reverse('downloads:download_bundles'),
            ]

            # Redirect if the requested path is not in the excluded list
            if request.path not in excluded_urls:
                return redirect('common:maintenance')

        response = self.get_response(request)
        return response


class BlockUserAgentMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        self.blocked_user_agents = [
            "bytespider",
            "bytedance",
            "tiktok",
            "dataforseo",
            "amazon",
            "bing",
        ]

    def __call__(self, request):
        user_agent = request.META.get('HTTP_USER_AGENT', '')
        for agent in self.blocked_user_agents:
            if agent in user_agent.lower():
                return HttpResponseForbidden("<h1>403 Forbidden</h1>Access denied for this user agent.")

        response = self.get_response(request)
        return response