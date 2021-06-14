from django.shortcuts import render, reverse, redirect, get_object_or_404
from django.db.models import F

from yeastphenome.apps.phenotypes.models import Observable
from yeastphenome.apps.datasets.models import Dataset

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
            "links": links,
            "active": "explorer",
        },
    )

@ratelimit(key="ip", rate=rl_rate, block=rl_block)
def phenotype_detail(request, phenotype_id):
    observable = get_object_or_404(Observable, pk=phenotype_id)
    datasets = get_datasets(observable)
    num_datasets = datasets.count()

    context = {
        "observable": observable,
        "datasets": datasets[:10],
        "num_datasets": num_datasets,
    }

    return render(request, "phenotypes/detail_min.html", context)


@ratelimit(key="ip", rate=rl_rate, block=rl_block)
def phenotype_datasets(request, phenotype_id):
    observable = get_object_or_404(Observable, pk=phenotype_id)
    datasets = get_datasets(observable)
    num_datasets = datasets.count()

    context = {
        "observable": observable,
        "datasets": datasets,
        "num_datasets": num_datasets,
    }

    return render(request, "phenotypes/datasets_min.html", context)


def get_datasets(observable):

    datasets = Dataset.objects.all_valid()
    datasets = datasets.filter(phenotype__observable=observable)
    datasets = datasets.values(dataset_id=F("id"),
                               dataset_paper_name=F("paper__systematic_name"),
                               dataset_phenotype_name=F("phenotype__name"),
                               dataset_conditionset_name=F("conditionset__display_name"),
                               dataset_medium_name=F("medium__display_name"),
                               dataset_collection_name=F("collection__shortname"),
                               dataset_data_name=F("data_available__name"))
    return datasets

