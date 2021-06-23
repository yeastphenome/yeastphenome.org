from django.shortcuts import render, redirect
from django.contrib import messages
from django.http import HttpResponse, JsonResponse
from django.views.decorators.cache import never_cache
from django.db.models import F

from yeastphenome.apps.datasets.models import Dataset, Data

from ratelimit.decorators import ratelimit
from yeastphenome.settings import (
    VIEW_RATE_LIMIT as rl_rate,
    VIEW_RATE_LIMIT_BLOCK as rl_block,
    DOWNLOAD_CART_LIMIT,
    DOWNLOAD_PREFIX,
)

import pandas as pd


@never_cache
@ratelimit(key="ip", rate=rl_rate, block=rl_block)
def download_bundles(request):
    context = {}
    return render(request, "downloads/bundles.html", context)


@never_cache
@ratelimit(key="ip", rate=rl_rate, block=rl_block)
def view_cart(request):

    if "cart" not in request.session:
        request.session["cart"] = []
    dataset_ids = request.session["cart"]

    datasets = Dataset.objects.all_valid().filter(id__in=dataset_ids)
    datasets = datasets.values(
        dataset_id=F("id"),
        dataset_paper_name=F("paper__systematic_name"),
        dataset_phenotype_name=F("phenotype__name"),
        dataset_conditionset_name=F("conditionset__display_name"),
        dataset_medium_name=F("medium__display_name"),
        dataset_collection_name=F("collection__shortname"),
        dataset_data_name=F("data_available__name"),
    )
    num_datasets = datasets.count()

    context = {
        "datasets": datasets,
        "num_datasets": num_datasets,
    }

    return render(request, "downloads/view_cart.html", context)


def add_to_cart(request, datasets_to_add):

    if not isinstance(datasets_to_add, list):
        datasets_to_add = [datasets_to_add]

    if "cart" not in request.session:
        request.session["cart"] = []

    datasets_in_cart = request.session["cart"]
    nr_datasets_in_cart = len(datasets_in_cart)
    nr_datasets_to_add = len(datasets_to_add)

    if nr_datasets_in_cart + nr_datasets_to_add > DOWNLOAD_CART_LIMIT:
        message = (
            "You cannot add more than <strong>%s datasets</strong> to the Download cart. "
            "Current cart size: <strong>%s datasets</strong>."
            % (DOWNLOAD_CART_LIMIT, nr_datasets_in_cart)
        )
        messages.info(request, message)
        status = "fail"

    else:

        request.session["cart"] += datasets_to_add
        # message = "%d datasets were added to your Download Cart." % nr_datasets_to_add
        # messages.success(request, message)
        message = ""
        status = "success"

    return JsonResponse({"message": message, "status": status})


def remove_from_cart(request, datasets_to_remove):

    if not isinstance(datasets_to_remove, list):
        datasets_to_remove = [datasets_to_remove]

    datasets_in_cart = request.session["cart"] if "cart" in request.session else []
    datasets_in_cart = [
        dataset for dataset in datasets_in_cart if dataset not in datasets_to_remove
    ]
    request.session["cart"] = datasets_in_cart
    request.session.modified = True

    # message = "Download cart updated."
    # messages.info(request, message)

    return JsonResponse({"status": "success"})


@ratelimit(key="ip", rate=rl_rate, block=rl_block)
def download_cart(request):
    datasets_in_cart = request.session["cart"] if "cart" in request.session else []
    data = Data.objects.all_valid().filter(dataset_id__in=datasets_in_cart)

    data = data.values(
        dataset_name=F("dataset__name"),
        gene_name=F("gene__systematic_name"),
        score=F("valuez"),
    )
    data_df = pd.DataFrame(list(data))
    data_df["score"] = pd.to_numeric(data_df["score"], errors="coerce")

    data_df_matrix = pd.pivot_table(
        data_df, index="gene_name", columns="dataset_name", values="score"
    )

    filename = "%s_datasets.txt" % (DOWNLOAD_PREFIX)

    # Prepare the HttpResponse
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = "attachment; filename=%s" % filename
    response["Set-Cookie"] = "fileDownload=true; path=/"
    response["X-Frame-Options"] = "ALLOWALL"

    # Print data matrix to response buffer
    data_df_matrix.to_csv(path_or_buf=response, sep="\t", index=True)

    return response


@ratelimit(key="ip", rate=rl_rate, block=rl_block)
def clear_cart(request):
    if "cart" in request.session:
        del request.session["cart"]
    return redirect("downloads:view_cart")
