from django.shortcuts import render, reverse, redirect
from django.http import HttpResponse
from django.views.decorators.cache import never_cache
from django.db.models import Q
from django.contrib.postgres.aggregates.general import StringAgg, BoolOr

from yeastphenome.apps.common.utils import (
    get_latest_stats_basic,
    get_latest_stats,
)
from yeastphenome.apps.datasets.models import Source
from yeastphenome.apps.papers.models import Paper
from yeastphenome.apps.papers.graphs import get_papers_by_year

from ratelimit.decorators import ratelimit
from yeastphenome.settings import (
    VIEW_RATE_LIMIT as rl_rate,
    VIEW_RATE_LIMIT_BLOCK as rl_block,
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
    return render(request, "main/index_min.html", context)


@ratelimit(key="ip", rate=rl_rate, block=rl_block)
def support(request):
    context = {}
    return render(request, "main/support.html", context)


@ratelimit(key="ip", rate=rl_rate, block=rl_block)
def about(request):
    return redirect("common:project")


@ratelimit(key="ip", rate=rl_rate, block=rl_block)
def project(request):
    context = {}
    return render(request, "main/project.html", context)


@ratelimit(key="ip", rate=rl_rate, block=rl_block)
def faq(request):
    context = {}
    return render(request, "main/faq.html", context)


@ratelimit(key="ip", rate=rl_rate, block=rl_block)
def stats(request):
    context = get_latest_stats()
    context["paper_counts"] = get_papers_by_year()
    return render(request, "main/stats.html", context)


@ratelimit(key="ip", rate=rl_rate, block=rl_block)
def authors(request):
    context = {}
    return render(request, "main/authors.html", context)


@ratelimit(key="ip", rate=rl_rate, block=rl_block)
def data_contributors(request):
    papers = (
        Paper.objects.all_valid()
        .filter(
            Q(datasets__data_source__acknowledge=True)
            | Q(datasets__tested_source__acknowledge=True)
        )
        .distinct()
    )

    # Using queryset annotation to pre-fetch all the relevant data and speed up the loading of the page
    agg_field1 = "datasets__data_source__label"
    agg_field2 = "datasets__tested_source__label"
    agg_field3 = "datasets__data_source__acknowledge"
    agg_field4 = "datasets__tested_source__acknowledge"
    papers = papers.annotate(
        people1=StringAgg(agg_field1, delimiter=", ", distinct=True)
    )
    papers = papers.annotate(
        people2=StringAgg(agg_field2, delimiter=", ", distinct=True)
    )
    papers = papers.annotate(data_ack=BoolOr(agg_field3))
    papers = papers.annotate(tested_ack=BoolOr(agg_field4))

    papers_values = list(
        papers.values(
            "id", "systematic_name", "people1", "people2", "data_ack", "tested_ack"
        )
    )

    def merge_people(paper_dict):
        people1 = paper_dict["people1"].split(", ")
        people2 = paper_dict["people2"].split(", ")
        people = list(itertools.chain.from_iterable([people1, people2]))
        people = [
            person for person in people if not person == "" and person is not None
        ]
        # A hack to avoid showing other sources (that don't need to be acknowledged) by accident (to be fixed)
        people = [
            person
            for person in people
            if not person.startswith("Table")
            and not person.startswith("T1-T2")
            and not person.startswith("MOESM")
        ]
        people = list(set(people))
        paper_dict["people"] = "; ".join(people)
        return paper_dict

    papers_values = [merge_people(paper_dict) for paper_dict in papers_values]

    num_people_to_ack = len(Source.objects.people_to_acknowledge())

    context = {
        "active": "about",
        "papers_list": papers_values,
        "num_people_to_ack": num_people_to_ack,
        "links": [
            {"url": reverse("common:about"), "name": "About"},
            {"url": reverse("common:data_contributors"), "name": "Data Contributors"},
        ],
    }

    return render(request, "main/data_contributors.html", context)


# Warmup requests (for app engine)
def warmup():
    return HttpResponse(status=200)

