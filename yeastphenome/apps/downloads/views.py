from django.shortcuts import render
from django.views.decorators.cache import never_cache

from ratelimit.decorators import ratelimit
from yeastphenome.settings import (
    VIEW_RATE_LIMIT as rl_rate,
    VIEW_RATE_LIMIT_BLOCK as rl_block
)


@never_cache
@ratelimit(key="ip", rate=rl_rate, block=rl_block)
def download_bundles(request):
    context = {}
    return render(request, "downloads/bundles.html", context)

