import re

from itertools import chain

from django.conf import settings
from django.core.paginator import Paginator
from django.shortcuts import render
from django.views import generic

from yeastphenome.apps.conditions.models import ConditionType, ConditionSet, Medium
from yeastphenome.apps.datasets.models import Dataset

from yeastphenome.apps.conditions.search import (
    get_search_tags,
    run_search_tag_query,
    get_querysets,
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

    queryset1, queryset2 = get_querysets()
    queryset = list(chain(queryset1, queryset2))

    if "q" in request.GET:
        q = request.GET["q"].strip()
        queryset = run_search_tag_query(q, return_instances=True)

    # 50 results per page
    paginator = Paginator(queryset, 50)
    page = request.GET.get("page")
    return render(
        request,
        "conditions/explorer.html",
        {"queryset": paginator.get_page(page), "tags": get_search_tags()},
    )


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
