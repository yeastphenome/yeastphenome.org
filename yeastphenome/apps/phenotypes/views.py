from django.conf import settings
from django.views import generic
from django.shortcuts import render, reverse, redirect, get_object_or_404
from django.db import models
from django.db.models import F

from yeastphenome.apps.phenotypes.models import Observable, Tag
from yeastphenome.apps.phenotypes.search import get_search_tags
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

    taglist = []
    links = [
        {"url": reverse("common:explorer"), "name": "Explore data"},
        {"url": reverse("phenotypes:index"), "name": "Phenotypes"},
    ]
    for key in [
        "observable",
        "tags",
        "phenotype",
        "measurement",
        "query",
    ]:
        for tag in request.GET.get(key, "").split("|"):
            if not tag:
                continue
            taglist.append({"value": tag, "code": key})

    print(taglist)
    return render(
        request,
        "phenotypes/explorer.html",
        {
            "taglist": taglist,
            "tags": get_search_tags(),
            "links": links,
            "active": "explorer",
        },
    )


@ratelimit(key="ip", rate=rl_rate, block=rl_block)
def phenotypes_by_tag(request, tag_id):
    tag = get_object_or_404(Tag, pk=tag_id)

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
    pheno = get_object_or_404(Observable, pk=phenotype_id)
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


def phenotype_detail(request, phenotype_id):
    observable = get_object_or_404(Observable, pk=phenotype_id)
    datasets = observable.phenotype_set.values(dataset_id=F("dataset__id"),
                                              dataset_paper_name=F("dataset__paper__systematic_name"),
                                              dataset_phenotype_name=F("dataset__phenotype__name"),
                                              dataset_conditionset_name=F("dataset__conditionset__display_name"),
                                              dataset_medium_name=F("dataset__medium__display_name"),
                                              dataset_collection_name=F("dataset__collection__shortname"),
                                              dataset_data_name=F("dataset__data_available__name"))
    num_datasets = datasets.count()

    context = {
        "phenotype": observable,
        "datasets": datasets[:10],
        "num_datasets": num_datasets,
    }

    return render(request, "phenotypes/detail_min.html", context)


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
                "name": context["object"].name,
            },
        ]

        # most similar tags, sort highest on top
        qs = Observable.objects.all().annotate(count=models.Count("pk"))
        qs = qs.filter(tags__in=context["object"].tags.all())
        context["similar"] = qs.order_by("-count").filter(count__gte=3).order_by("name")
        context["sorted_tags"] = context["object"].tags.all().order_by("name")
        context["active"] = "explorer"

        # list of "sibling" phenotypes -- phenotypes that share the same observable
        context["siblings"] = (
            context["object"].phenotype_set.all().exclude(observable=context["object"])
        )
        context["id"] = context["object"].id
        return context
