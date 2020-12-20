from django.db.models import Count
from django.conf import settings
from django.shortcuts import reverse, render, redirect, get_object_or_404
from django.views import generic

from yeastphenome.apps.conditions.models import ConditionType, ConditionSet, Medium, Tag
from yeastphenome.apps.conditions.search import get_search_tags

from ratelimit.mixins import RatelimitMixin
from ratelimit.decorators import ratelimit
from yeastphenome.settings import (
    VIEW_RATE_LIMIT as rl_rate,
    VIEW_RATE_LIMIT_BLOCK as rl_block,
)


@ratelimit(key="ip", rate=rl_rate, block=rl_block)
def index(request):
    """the conditions explorer uses a server side rendered table, which we
    generate by passing along a taglist to the view
    """
    taglist = []
    links = [
        {"url": reverse("common:explorer"), "name": "Explore data"},
        {"url": reverse("conditions:index"), "name": "Conditions"},
    ]
    for tag in request.GET.get("query", "").split("|"):
        if not tag:
            continue
        taglist.append({"value": tag, "code": "query"})

    return render(
        request,
        "conditions/explorer.html",
        {
            "taglist": taglist,
            "tags": get_search_tags(),
            "links": links,
            "active": "explorer",
        },
    )


@ratelimit(key="ip", rate=rl_rate, block=rl_block)
def redirect_index(request):
    return redirect("conditions:index")


@ratelimit(key="ip", rate=rl_rate, block=rl_block)
def tag_browser(request):
    """View a listing of tags"""
    tags = Tag.all_valid()
    links = [
        {"url": reverse("common:explorer"), "name": "Explore data"},
        {"url": reverse("conditions:index"), "name": "Conditions"},
        {"url": reverse("conditions:index"), "name": "Condition Tags"},
    ]
    return render(
        request,
        "conditions/tag_browser.html",
        {"tags": tags, "links": links, "active": "explorer"},
    )


@ratelimit(key="ip", rate=rl_rate, block=rl_block)
def browse(request):
    """Browse dataest by condition names (and size by count)"""
    # With >=1 dataset, sorted by datasets
    qs = (
        ConditionType.all_valid()
        .annotate(
            number_of_papers=Count(
                "condition__conditionset__dataset__paper", distinct=True
            )
        )
        .order_by("-number_of_datasets")
    )

    links = [
        {"url": reverse("common:explorer"), "name": "Explore data"},
        {"url": reverse("conditions:index"), "name": "Conditions"},
        {"url": reverse("conditions:browse"), "name": "Browse Conditions"},
    ]
    context = {"data": qs[:100], "active": "explorer", "links": links}
    return render(request, "conditions/graphs/browse.html", context)


class ConditiontypeDetailView(generic.DetailView, RatelimitMixin):
    model = ConditionType
    template_name = "conditions/detail.html"
    ratelimit_key = "ip"
    ratelimit_rate = rl_rate
    ratelimit_block = rl_block

    def get_context_data(self, **kwargs):
        context = super(ConditiontypeDetailView, self).get_context_data(**kwargs)
        context["DOWNLOAD_PREFIX"] = settings.DOWNLOAD_PREFIX
        context["USER_AUTH"] = self.request.user.is_authenticated
        context["papers"] = context["object"].datasets
        context["id"] = context["object"].id
        context["active"] = "explorer"
        context["module"] = "conditions"
        context["links"] = [
            {"url": reverse("common:explorer"), "name": "Explore data"},
            {"url": reverse("conditions:index"), "name": "Conditions"},
            {
                "url": reverse("conditions:detail", args=[context["object"].id]),
                "name": context["object"].name,
            },
        ]
        return context


@ratelimit(key="ip", rate=rl_rate, block=rl_block)
def conditions_by_tag(request, tag_id):
    tag = get_object_or_404(Tag, pk=tag_id)

    links = [
        {"url": reverse("common:explorer"), "name": "Explore data"},
        {"url": reverse("conditions:index"), "name": "Conditions"},
        {"url": reverse("conditions:tags"), "name": "Tags"},
        {"url": reverse("conditions:tag", args=[tag.id]), "name": tag.name},
    ]
    return render(request, "conditions/tag.html", {"tag": tag, "links": links})


class MediumDetailView(generic.DetailView, RatelimitMixin):
    model = Medium
    template_name = "conditions/medium_detail.html"
    ratelimit_key = "ip"
    ratelimit_rate = rl_rate
    ratelimit_block = rl_block

    def get_context_data(self, **kwargs):
        context = super(MediumDetailView, self).get_context_data(**kwargs)
        context["DOWNLOAD_PREFIX"] = settings.DOWNLOAD_PREFIX
        context["USER_AUTH"] = self.request.user.is_authenticated
        context["datasets"] = context["object"].datasets
        context["active"] = "explorer"
        context["id"] = context["object"].id
        context["template"] = "medium"
        context["links"] = [
            {"url": reverse("common:explorer"), "name": "Explore data"},
            {"url": reverse("conditions:index"), "name": "Conditions"},
            {
                "url": "%s?medium=%s"
                % (reverse("conditions:index"), context["object"].display_name),
                "name": "Medium",
            },
            {
                "url": reverse("conditions:medium_detail", args=[context["object"].id]),
                "name": context["object"].display_name,
            },
        ]
        return context


class ConditionSetDetailView(generic.DetailView, RatelimitMixin):
    model = ConditionSet
    template_name = "conditions/conditionset_detail.html"
    ratelimit_key = "ip"
    ratelimit_rate = rl_rate
    ratelimit_block = rl_block

    def get_context_data(self, **kwargs):
        context = super(ConditionSetDetailView, self).get_context_data(**kwargs)
        context["DOWNLOAD_PREFIX"] = settings.DOWNLOAD_PREFIX
        context["USER_AUTH"] = self.request.user.is_authenticated
        context["datasets"] = context["object"].datasets
        context["active"] = "explorer"
        context["id"] = context["object"].id
        context["links"] = [
            {"url": reverse("common:explorer"), "name": "Explore data"},
            {"url": reverse("conditions:index"), "name": "Conditions"},
            {
                "url": reverse(
                    "conditions:conditionset_detail", args=[context["object"].id]
                ),
                "name": context["object"].systematic_name,
            },
        ]
        return context
