import re

from django.db import models
from django.conf import settings
from django.core.paginator import Paginator
from django.shortcuts import reverse, render
from django.views import generic
from django.http import Http404

# from django.views.decorators.cache import never_cache
from yeastphenome.apps.conditions.models import ConditionType, ConditionSet, Medium, Tag
from yeastphenome.apps.datasets.models import Dataset

from yeastphenome.apps.conditions.search import (
    get_search_tags,
    run_search_tag_query,
)

from libchebipy import ChebiEntity

from ratelimit.mixins import RatelimitMixin
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
    links = [{"url": reverse("conditions:index"), "name": "Condition Explorer"}]
    for key in [
        "pubchem_name",
        "other_name",
        "chebi_name",
        "name",
        "tag",
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
        "conditions/explorer.html",
        {
            "queryset": queryset,
            "tags": get_search_tags(),
            "links": links,
            "active": "explorer",
        },
    )


@ratelimit(key="ip", rate=rl_rate, block=rl_block)
def browse(request):
    """Browse dataest by condition names (and size by count)"""
    qs = (
        ConditionType.objects.all()
        .annotate(
            not_relevant_datasets=models.Count(
                models.Case(
                    models.When(
                        condition__conditionset__dataset__paper__latest_data_status__status__name="not relevant",
                        then=1,
                    )
                )
            )
        )
        .annotate(total_datasets=models.Count("condition__conditionset__dataset"))
        .annotate(
            number_of_papers=models.Count(
                "condition__conditionset__dataset__paper", distinct=True
            )
        )
        .annotate(
            number_of_datasets=models.F("total_datasets")
            - models.F("not_relevant_datasets")
        )
        .order_by("-number_of_datasets")
    )

    context = {"data": qs[:100]}
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
        context["links"] = [
            {"url": reverse("conditions:index"), "name": "Condition Explorer"},
            {
                "url": reverse("conditions:detail", args=[context["object"].id]),
                "name": "Condition (%s)" % context["object"].name,
            },
        ]
        return context


@ratelimit(key="ip", rate=rl_rate, block=rl_block)
def conditionclass(request, class_id):
    class_entity = ChebiEntity("CHEBI:" + str(class_id))
    class_name = class_entity.get_name()
    children = []
    for relation in class_entity.get_incomings():
        if relation.get_type() == "has_role":
            tid = relation.get_target_chebi_id()
            tid = re.search("(?<=CHEBI:)(\d)*", tid)
            tid = int(tid.group(0))
            children.append(tid)

    conditiontypes = ConditionType.objects.filter(chebi_id__in=children)
    datasets = (
        Dataset.objects.filter(conditionset__conditions__type__in=conditiontypes)
        .exclude(paper__latest_data_status__status__name="not relevant")
        .distinct()
    )
    return render(
        request,
        "conditions/class.html",
        {
            "id": class_id,
            "class_name": class_name,
            "conditiontypes": conditiontypes,
            "papers": datasets,
            "DOWNLOAD_PREFIX": settings.DOWNLOAD_PREFIX,
            "USER_AUTH": request.user.is_authenticated,
        },
    )


@ratelimit(key="ip", rate=rl_rate, block=rl_block)
def conditions_by_tag(request, tag_id):
    try:
        tag = Tag.objects.get(id=tag_id)
    except Tag.DoesNotExist:
        raise Http404

    return render(request, "conditions/tag.html", {"tag": tag})


class MediumDetailView(generic.DetailView, RatelimitMixin):
    model = Medium
    template_name = "conditions/conditionset_medium_detail.html"
    ratelimit_key = "ip"
    ratelimit_rate = rl_rate
    ratelimit_block = rl_block

    def get_context_data(self, **kwargs):
        context = super(MediumDetailView, self).get_context_data(**kwargs)
        context["DOWNLOAD_PREFIX"] = settings.DOWNLOAD_PREFIX
        context["USER_AUTH"] = self.request.user.is_authenticated
        context["papers"] = context["object"].datasets
        context["id"] = context["object"].id
        return context


class ConditionSetDetailView(generic.DetailView, RatelimitMixin):
    model = ConditionSet
    template_name = "conditions/conditionset_medium_detail.html"
    ratelimit_key = "ip"
    ratelimit_rate = rl_rate
    ratelimit_block = rl_block

    def get_context_data(self, **kwargs):
        context = super(ConditionSetDetailView, self).get_context_data(**kwargs)
        context["DOWNLOAD_PREFIX"] = settings.DOWNLOAD_PREFIX
        context["USER_AUTH"] = self.request.user.is_authenticated
        context["papers"] = context["object"].datasets
        context["id"] = context["object"].id
        return context
