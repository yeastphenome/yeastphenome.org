from django.http import HttpResponseForbidden

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