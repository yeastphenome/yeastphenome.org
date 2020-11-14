from django.core.paginator import Paginator
from django.conf import settings
from django.views import generic
from django.shortcuts import render, reverse, redirect
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
def redirect_index(request):
    return redirect("phenotypes:index")


@ratelimit(key="ip", rate=rl_rate, block=rl_block)
def index(request):

    # Count == 0 indicates a search, no search is set to None
    queryset = []
    count = None
    taglist = []
    links = [
        {"url": reverse("common:explorer"), "name": "Explore data"},
        {"url": reverse("phenotypes:index"), "name": "Phenotypes"},
    ]
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
    links = [
        {"url": reverse("common:explorer"), "name": "Explore data"},
        {"url": reverse("phenotypes:index"), "name": "Phenotypes"},
        {
            "url": reverse("phenotypes:tag", args=[tag.id]),
            "name": "Tag: %s" % tag.name,
        },
    ]
    context = {"tag": tag, "links": links, "module": "phenotypes"}
    return render(request, "phenotypes/tag.html", context)


@ratelimit(key="ip", rate=rl_rate, block=rl_block)
def phenotypes_by_tags(request, phenotype_id):
    """phenotypes by tags looks up an observable, and returns all phenotypes that
    have all tags
    """
    try:
        pheno = Observable.objects.get(id=phenotype_id)
    except Observable.DoesNotExist:
        raise Http404
    tag_names = ",".join([x.name for x in pheno.tags.all()])

    # Filter down observables to those with all tags
    queryset = Observable.objects.all()
    for tag in pheno.tags.all():
        queryset = queryset.filter(tags__name=tag.name)

    links = [
        {"url": reverse("common:explorer"), "name": "Explore data"},
        {"url": reverse("phenotypes:index"), "name": "Phenotypes"},
        {
            "url": reverse("phenotypes:tag", args=[tag.id]),
            "name": "Tags: %s" % tag_names,
        },
    ]
    context = {"links": links, "names": tag_names, "observables": queryset}
    return render(request, "phenotypes/tags.html", context)


class ObservableDetailView(generic.DetailView):
    model = Observable
    template_name = "phenotypes/detail.html"

    def get_context_data(self, **kwargs):
        context = super(ObservableDetailView, self).get_context_data(**kwargs)
        context["DOWNLOAD_PREFIX"] = settings.DOWNLOAD_PREFIX
        context["USER_AUTH"] = self.request.user.is_authenticated
        context["module"] = "phenotypes"
        context["links"] = [
            {"url": reverse("common:explorer"), "name": "Explore data"},
            {"url": reverse("phenotypes:index"), "name": "Phenotypes"},
            {
                "url": reverse("phenotypes:detail", args=[context["object"].id]),
                "name": "Mitophagy",
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
