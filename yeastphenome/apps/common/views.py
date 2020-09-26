from django.shortcuts import render, redirect
from django.contrib import messages
from django.http import HttpResponse, JsonResponse
from django.views.decorators.cache import never_cache

from yeastphenome.apps.common.forms import SearchForm
from yeastphenome.apps.common.utils import (
    get_dataset_sources,
    get_latest_stats,
    select_random_graph,
    get_papers_by_year,
    get_phenotype_measurements,
)
from yeastphenome.apps.datasets.models import Dataset
from yeastphenome.apps.papers.models import Paper

from ratelimit.decorators import ratelimit
from yeastphenome.settings import (
    VIEW_RATE_LIMIT as rl_rate,
    VIEW_RATE_LIMIT_BLOCK as rl_block,
)

# Core Pages


@ratelimit(key="ip", rate=rl_rate, block=rl_block)
def index(request):

    form = SearchForm()
    context = get_latest_stats()

    # Most Recently added, most recently updated
    context["paper"] = Paper.objects.latest("pub_date")
    context["paper_latest"] = Paper.objects.latest()
    context["form"] = form

    # Select a random graph to add to the context
    context.update(select_random_graph())
    return render(request, "main/index.html", context)


@ratelimit(key="ip", rate=rl_rate, block=rl_block)
def about(request):
    return render(request, "main/about.html")


@ratelimit(key="ip", rate=rl_rate, block=rl_block)
def faq(request):
    return render(request, "main/faq.html")


@ratelimit(key="ip", rate=rl_rate, block=rl_block)
def stats(request):
    context = get_latest_stats()
    context["paper_counts"] = get_papers_by_year()
    context.update(get_phenotype_measurements(hide_legend=True))
    context.update(get_dataset_sources())
    return render(request, "main/stats.html", context)


@ratelimit(key="ip", rate=rl_rate, block=rl_block)
def contributors(request):
    return render(request, "main/contributors.html")


# Warmup requests (for app engine)


def warmup():
    return HttpResponse(status=200)


# Getting Started Pages


@ratelimit(key="ip", rate=rl_rate, block=rl_block)
def getting_started(request):
    return render(request, "getting-started/getting-started.html")


@ratelimit(key="ip", rate=rl_rate, block=rl_block)
def background(request):
    return render(request, "getting-started/background.html")


@ratelimit(key="ip", rate=rl_rate, block=rl_block)
def advanced(request):
    return render(request, "getting-started/advanced.html")


@ratelimit(key="ip", rate=rl_rate, block=rl_block)
def tutorials(request):
    return render(request, "getting-started/tutorials.html")


@ratelimit(key="ip", rate=rl_rate, block=rl_block)
def introduction(request):
    return render(request, "getting-started/introduction.html")


# Cart Operations


@ratelimit(key="ip", rate=rl_rate, block=rl_block)
def add_to_cart(request, dataset_id, next=None):
    """Add one or more datasets to the cart, if they exist. A dataset id
    can be a single string of values, comma separted, or just the value.
    If the request is a POST, we assume coming from a page and return
    a message as JSON.
    """
    if "cart" not in request.session:
        request.session["cart"] = []

    added_count = 0
    for d_id in dataset_id.split(","):
        dataset = Dataset.objects.get(id=d_id)
        if dataset.id not in request.session["cart"]:
            request.session["cart"].append(dataset.id)
            request.session.modified = True
            added_count += 1

    if added_count == 1:
        message = "1 dataset was added to your cart."
    else:
        message = "%s datasets were added to your cart." % added_count

    # Return to the same page the user was browsing
    if request.method == "POST":
        return JsonResponse({"message": message})

    messages.success(request, message)
    if next is not None:
        return redirect(next)
    return redirect("common:view_cart")


@ratelimit(key="ip", rate=rl_rate, block=rl_block)
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
        return JsonResponse({"message": message})

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
def view_cart(request):
    """View all datasets in the cart, and provide a button to download."""
    cart = request.session.get("cart", [])
    print(cart)
    context = {"datasets": Dataset.objects.filter(id__in=cart)}
    return render(request, "cart/view_cart.html", context)
