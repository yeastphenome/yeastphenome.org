from django.shortcuts import render, redirect
from django.contrib import messages

from yeastphenome.apps.common.forms import SearchForm
from yeastphenome.apps.common.utils import get_latest_stats, get_papers_by_year
from yeastphenome.apps.datasets.models import Dataset

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
    context["form"] = form
    context["paper_counts"] = get_papers_by_year()
    return render(request, "base/index.html", context)


@ratelimit(key="ip", rate=rl_rate, block=rl_block)
def about(request):

    context = get_latest_stats()

    return render(request, "main/about.html", context)


@ratelimit(key="ip", rate=rl_rate, block=rl_block)
def getting_started(request):
    return render(request, "main/getting-started.html")


@ratelimit(key="ip", rate=rl_rate, block=rl_block)
def data_explorer(request):
    return render(request, "main/data-explorer.html")


# Cart Operations


@ratelimit(key="ip", rate=rl_rate, block=rl_block)
def add_to_cart(request, dataset_id, next=None):
    """Add a dataset to the cart, if it exists.
    """
    try:
        dataset = Dataset.objects.get(id=dataset_id)
        if "cart" not in request.session:
            request.session["cart"] = []
        if dataset.id not in request.session["cart"]:
            request.session["cart"].append(dataset.id)
        request.session.modified = True
        messages.success(
            request, "Dataset with id %s was added to your download cart." % dataset_id
        )
    except:
        messages.info(request, "Dataset with id %s does not exist" % dataset_id)

    # Return to the same page the user was browsing
    if next is not None:
        return redirect(next)
    return redirect("common:view_cart")


@ratelimit(key="ip", rate=rl_rate, block=rl_block)
def remove_from_cart(request, dataset_id, next=None):
    """Remove a dataset from the cart, if it exists.
    """
    dataset_id = int(dataset_id)
    if "cart" in request.session and dataset_id in request.session["cart"]:
        request.session["cart"].pop(request.session["cart"].index(dataset_id))
        request.session.modified = True
        messages.success(
            request,
            "Dataset with id %s was removed from your download cart." % dataset_id,
        )
    else:
        messages.info(request, "Dataset with id %s is not in your cart." % dataset_id)

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


@ratelimit(key="ip", rate=rl_rate, block=rl_block)
def view_cart(request):
    """View all datasets in the cart, and provide a button to download.
    """
    context = {
        "datasets": Dataset.objects.filter(id__in=request.session.get("cart", []))
    }
    return render(request, "cart/view_cart.html", context)
