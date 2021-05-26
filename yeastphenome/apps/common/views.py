from django.shortcuts import render, redirect, reverse, get_object_or_404
from django.contrib import messages
from django.http import HttpResponse, JsonResponse, HttpResponseRedirect
from django.views.decorators.cache import never_cache
from django.db.models import Q
from django.contrib.postgres.aggregates.general import StringAgg, BoolOr

from yeastphenome.apps.common.utils import (
    check_download_space,
    get_latest_stats_basic,
    get_latest_stats,
)
from yeastphenome.apps.datasets.models import Dataset, Source
from yeastphenome.apps.papers.models import Paper
from yeastphenome.apps.papers.graphs import get_papers_by_year
from yeastphenome.apps.conditions.models import ConditionType, Medium
from yeastphenome.apps.phenotypes.models import Observable

from ratelimit.decorators import ratelimit
from yeastphenome.settings import (
    VIEW_RATE_LIMIT as rl_rate,
    VIEW_RATE_LIMIT_BLOCK as rl_block,
    DOWNLOAD_CART_LIMIT,
)

import itertools


def handler404(request, exception):
    response = render(request, "base/404.html", {})
    response.status_code = 404
    return response


@never_cache
@ratelimit(key="ip", rate=rl_rate, block=rl_block)
def index(request):
    context = get_latest_stats_basic()
    return render(request, "main/index.html", context)


@ratelimit(key="ip", rate=rl_rate, block=rl_block)
def support(request):
    links = [
        {"url": reverse("common:support"), "name": "Support"},
        {"url": reverse("common:support"), "name": "General and Data Inquiries"},
    ]
    context = {"links": links, "active": "support"}
    return render(request, "main/support.html", context)


@ratelimit(key="ip", rate=rl_rate, block=rl_block)
def about(request):
    links = [
        {"url": reverse("common:about"), "name": "About"},
    ]
    context = {"active": "about", "links": links}
    return render(request, "main/about.html", context)


@ratelimit(key="ip", rate=rl_rate, block=rl_block)
def project(request):
    links = [
        {"url": reverse("common:about"), "name": "About"},
        {"url": reverse("common:about"), "name": "Project"},
    ]
    context = {"active": "about", "links": links}
    return render(request, "main/project.html", context)


@ratelimit(key="ip", rate=rl_rate, block=rl_block)
def faq(request):
    links = [
        {"url": reverse("common:about"), "name": "About"},
        {"url": reverse("common:faq"), "name": "Frequently Asked Questions"},
    ]
    context = {"active": "about", "links": links}
    return render(request, "main/faq.html", context)


@ratelimit(key="ip", rate=rl_rate, block=rl_block)
def stats(request):
    context = get_latest_stats()
    context["active"] = "about"
    context["links"] = [
        {"url": reverse("common:about"), "name": "About"},
        {"url": reverse("common:stats"), "name": "Stats"},
    ]
    context["paper_counts"] = get_papers_by_year()
    return render(request, "main/stats.html", context)


@ratelimit(key="ip", rate=rl_rate, block=rl_block)
def authors(request):
    links = [
        {"url": reverse("common:about"), "name": "About"},
        {"url": reverse("common:contributors"), "name": "Authors"},
    ]
    context = {"active": "about", "links": links}
    return render(request, "main/authors.html", context)


@ratelimit(key="ip", rate=rl_rate, block=rl_block)
def data_contributors(request):
    papers = Paper.objects.all_valid().filter(
        Q(datasets__data_source__acknowledge=True)
        | Q(datasets__tested_source__acknowledge=True)
    ).distinct()

    # Using queryset annotation to pre-fetch all the relevant data and speed up the loading of the page
    agg_field1 = "datasets__data_source__label"
    agg_field2 = "datasets__tested_source__label"
    agg_field3 = "datasets__data_source__acknowledge"
    agg_field4 = "datasets__tested_source__acknowledge"
    papers = papers.annotate(people1=StringAgg(agg_field1, delimiter=", ", distinct=True))
    papers = papers.annotate(people2=StringAgg(agg_field2, delimiter=", ", distinct=True))
    papers = papers.annotate(data_ack=BoolOr(agg_field3))
    papers = papers.annotate(tested_ack=BoolOr(agg_field4))

    papers_values = list(papers.values("id", "systematic_name",
                                  "people1", "people2",
                                  "data_ack", "tested_ack"))

    def merge_people(paper_dict):
        people1 = paper_dict["people1"].split(', ')
        people2 = paper_dict["people2"].split(', ')
        people = list(itertools.chain.from_iterable([people1, people2]))
        people = [person for person in people if not person == "" and person is not None]
        people = list(set(people))
        paper_dict["people"] = "; ".join(people)
        return paper_dict

    papers_values = [merge_people(paper_dict) for paper_dict in papers_values]

    num_people_to_ack = len(Source.objects.people_to_acknowledge())

    context = {"active": "about",
               "papers_list": papers_values,
               "num_people_to_ack": num_people_to_ack,
               "links": [
                   {"url": reverse("common:about"), "name": "About"},
                   {"url": reverse("common:data_contributors"), "name": "Data Contributors"},
               ]}

    return render(request, "main/data_contributors.html", context)


# Warmup requests (for app engine)
def warmup():
    return HttpResponse(status=200)


# Explorer Home
@ratelimit(key="ip", rate=rl_rate, block=rl_block)
def explorer(request):
    links = [{"url": reverse("common:explorer"), "name": "Explore data"}]
    context = {"active": "explorer", "links": links}
    return render(request, "main/explorer.html", context)


# Download Operations
def add_bulk_datasets(request, datasets, return_message=False):
    """A shared function to retrieve the downloads from a request, and add bulk
    datasets to it
    """
    if "cart" not in request.session:
        request.session["cart"] = []

    if not check_download_space(request, datasets):
        message = (
            "You are limited to adding no more than %s datasets to your Download Cart."
            % DOWNLOAD_CART_LIMIT
        )
        if return_message:
            return "full", message
        messages.info(request, message)
        return

    added_count = 0
    for dataset in datasets:

        # The function can support an integer id or a dataset object
        if isinstance(dataset, Dataset):
            dataset = dataset.id
        if dataset not in request.session["cart"]:
            request.session["cart"].append(dataset)
            request.session.modified = True
            added_count += 1

    if added_count == 1:
        message = "1 dataset was added to your Download Cart."
    else:
        message = "%s datasets were added to your Download Cart." % added_count

    if return_message:
        return "success", message
    messages.success(request, message)


@ratelimit(key="ip", rate=rl_rate, block=rl_block)
def add_to_cart_by_conditiontype(request, conditiontype_id):
    """Add datasets to the cart based on a conditiontype id"""
    ct = get_object_or_404(ConditionType, pk=conditiontype_id)
    add_bulk_datasets(request, ct.datasets())
    return HttpResponseRedirect("/conditions/%s/" % ct.id)


@ratelimit(key="ip", rate=rl_rate, block=rl_block)
def add_to_cart_by_medium(request, medium_id):
    """Add datasets to the cart based on a medium id"""
    medium = get_object_or_404(Medium, pk=medium_id)
    add_bulk_datasets(request, medium.datasets())
    return HttpResponseRedirect("/conditions/media/%s/" % medium.id)


@ratelimit(key="ip", rate=rl_rate, block=rl_block)
def add_to_cart_by_paper(request, paper_id):
    """Add datasets to the cart based on a paper id"""
    paper = get_object_or_404(Paper, pk=paper_id)
    add_bulk_datasets(request, paper.dataset_set.all())
    return HttpResponseRedirect("/papers/%s/" % paper.id)


@ratelimit(key="ip", rate=rl_rate, block=rl_block)
def add_to_cart_by_observable(request, observable_id):
    """Add datasets to the cart based on a phenotype (observable) id"""
    observable = get_object_or_404(Observable, pk=observable_id)
    add_bulk_datasets(request, observable.datasets())
    return HttpResponseRedirect("/phenotypes/%s/" % observable.id)


def add_to_cart(request, dataset_id, next=None):
    """Add one or more datasets to the cart, if they exist. A dataset id
    can be a single string of values, comma separted, or just the value.
    If the request is a POST, we assume coming from a page and return
    a message as JSON.
    """
    if "cart" not in request.session:
        request.session["cart"] = []

    status, message = add_bulk_datasets(request, [int(dataset_id)], return_message=True)

    # Return to the same page the user was browsing
    if request.method == "POST":
        return JsonResponse({"message": message, "status": status})

    messages.success(request, message)
    if next is not None:
        return redirect(next)
    return redirect("common:view_cart")


def remove_from_cart(request, dataset_id, next=None):
    """Remove a dataset from the cart, if it exists."""
    dataset_id = int(dataset_id)
    if "cart" in request.session and dataset_id in request.session["cart"]:
        request.session["cart"].pop(request.session["cart"].index(dataset_id))
        request.session.modified = True
        message = "Dataset with id %s was removed from your download cart." % dataset_id
    else:
        message = "Dataset with id %s is not in your cart." % dataset_id

    if request.method == "POST":
        return JsonResponse({"message": message, "status": "success"})

    messages.info(request, message)

    # Return to the same page the user was browsing
    if next is not None:
        return redirect(next)
    return redirect("common:view_cart")


@ratelimit(key="ip", rate=rl_rate, block=rl_block)
def clear_cart(request):
    """remove all datasets from the session cart. We don't add a message because
    this view is only accessible from the View Cart page, and when it's cleared
    the user is shown a message that there are no items in the cart.
    """
    if "cart" in request.session:
        del request.session["cart"]
    return redirect("common:view_cart")


@never_cache
@ratelimit(key="ip", rate=rl_rate, block=rl_block)
def download_bundles(request):
    """A page with pre-prepared archives to download"""
    links = [
        {"url": reverse("common:view_cart"), "name": "Downloads"},
        {"url": reverse("common:download_bundles"), "name": "Bundle Downloads"},
    ]
    context = {"active": "downloads", "links": links}
    return render(request, "cart/bundles.html", context)


@never_cache
@ratelimit(key="ip", rate=rl_rate, block=rl_block)
def view_cart(request):
    """View all datasets in the cart, and provide a button to download."""
    links = [
        {"url": reverse("common:view_cart"), "name": "Downloads"},
        {"url": reverse("common:view_cart"), "name": "Download Cart"},
    ]
    cart = request.session.get("cart", [])
    context = {
        "datasets": Dataset.objects.filter(id__in=cart),
        "active": "downloads",
        "links": links,
    }
    return render(request, "cart/view_cart.html", context)
