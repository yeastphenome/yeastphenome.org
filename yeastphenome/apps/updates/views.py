from django.shortcuts import render

from yeastphenome.apps.updates.models import Update


def get_last_updates(n=2):

    updates_qs = Update.objects.order_by("-date")
    
    if not n:
        n = updates_qs.count()
    
    updates_qs = updates_qs[:n]
    updates_list_of_dict = list(updates_qs.values())

    return updates_list_of_dict


def index(request):

    context = {}
    context['last_updates'] = get_last_updates(n=None)
    return render(request, "updates/list.html", context)
