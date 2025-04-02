from django.shortcuts import render, redirect, get_object_or_404
from django.db.models import F

from yeastphenome.apps.phenotypes.models import Observable
from yeastphenome.apps.datasets.models import Dataset


def redirect_index(request):
    return redirect("phenotypes:index")


def index(request):
    return redirect("search:search")


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
    datasets = datasets.values(
        dataset_id=F("id"),
        dataset_paper_name=F("paper__systematic_name"),
        dataset_phenotype_name=F("phenotype__name"),
        dataset_conditionset_name=F("conditionset__display_name"),
        dataset_medium_name=F("medium__display_name"),
        dataset_collection_name=F("collection__shortname"),
        dataset_data_name=F("data_available__name"),
    )
    return datasets
