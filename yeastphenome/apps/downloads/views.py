from django.shortcuts import render
from django.views.decorators.cache import never_cache


@never_cache
def download_bundles(request):
    context = {}
    return render(request, "downloads/bundles.html", context)

