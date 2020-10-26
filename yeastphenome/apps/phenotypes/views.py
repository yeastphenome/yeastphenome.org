from django.core.paginator import Paginator
from django.conf import settings
from django.views import generic
from django.shortcuts import render, reverse
from django.db import models
from django.http import Http404

# from django.views.decorators.cache import never_cache
from yeastphenome.apps.phenotypes.models import Observable, Tag
from yeastphenome.apps.phenotypes.search import get_search_tags, run_search_tag_query

from ratelimit.decorators import ratelimit

from yeastphenome.settings import (
    VIEW_RATE_LIMIT as rl_rate,
    VIEW_RATE_LIMIT_BLOCK as rl_block,
)


@ratelimit(key="ip", rate=rl_rate, block=rl_block)
def index(request):

    # Count == 0 indicates a search, no search is set to None
    queryset = []
    count = None
    taglist = []
    links = [{"url": reverse("phenotypes:index"), "name": "Phenotype Explorer"}]
    for key in [
        "observable",
        "tag",
        "phenotype",
        "measurement",
        "query",
    ]:
        for tag in request.GET.get(key, "").split(","):
            if not tag:
                continue
            taglist.append({"value": tag, "code": key})

    if taglist:
        queryset = run_search_tag_query(query=None, taglist=taglist)

        # 50 results per page
        paginator = Paginator(queryset, 50)
        page = request.GET.get("page")
        queryset = paginator.get_page(page)
        count = len(queryset)

    queryset = {
        "results": queryset,
        "count": count,
    }

    return render(
        request,
        "phenotypes/explorer.html",
        {
            "queryset": queryset,
            "tags": get_search_tags(),
            "links": links,
            "active": "explorer",
        },
    )


@ratelimit(key="ip", rate=rl_rate, block=rl_block)
def phenotypes_by_tag(request, tag_id):
    try:
        tag = Tag.objects.get(id=tag_id)
    except Tag.DoesNotExist:
        raise Http404

    return render(request, "phenotypes/tag.html", {"tag": tag})


class ObservableDetailView(generic.DetailView):
    model = Observable
    template_name = "phenotypes/detail.html"

    def get_context_data(self, **kwargs):
        context = super(ObservableDetailView, self).get_context_data(**kwargs)
        context["DOWNLOAD_PREFIX"] = settings.DOWNLOAD_PREFIX
        context["USER_AUTH"] = self.request.user.is_authenticated
        context["links"] = [
            {"url": reverse("phenotypes:index"), "name": "Phenotype Explorer"},
            {
                "url": reverse("phenotypes:detail", args=[context["object"].id]),
                "name": "Phenotype %s" % context["object"].id,
            },
        ]

        # most similar tags, sort highest on top
        qs = Observable.objects.all().annotate(count=models.Count("pk"))
        qs = qs.filter(tags__in=context["object"].tags.all())
        context["similar"] = qs.order_by("-count").filter(count__gte=3)
        context["active"] = "explorer"

        # list of "sibling" phenotypes -- phenotypes that share the same observable
        context["siblings"] = (
            context["object"].phenotype_set.all().exclude(observable=context["object"])
        )
        context["id"] = context["object"].id
        return context
