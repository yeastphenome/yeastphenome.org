from django.views.decorators.cache import never_cache
from django.shortcuts import render

from elastic_enterprise_search import AppSearch

from yeastphenome.apps.common.forms import GlobalSearchForm
from yeastphenome.settings import (
    VIEW_RATE_LIMIT as rl_rate,
    VIEW_RATE_LIMIT_BLOCK as rl_block,
    ELASTICSEARCH_HOST,
    ELASTICSEARCH_AUTH,
)

from ratelimit.decorators import ratelimit

import numpy as np
import re


@never_cache
@ratelimit(key="ip", rate=rl_rate, block=rl_block)
def index(request):

    context = dict()

    if "q" in request.GET:

        form = GlobalSearchForm(request.GET)

        if form.is_valid():
            q = form.cleaned_data["q"]
        else:
            q = request.GET.get("q")

        q_list = re.split("[,; ]", q)
        q_list = [qi.strip() for qi in q_list]
        q_list = [qi for qi in q_list if qi]
        q_lucene = " AND ".join(q_list)
        q_lucene = '"' + q_lucene + '"'

        field = request.GET.get("field")

        page_number = int(request.GET.get("page", "1"))
        tab = request.GET.get("tab", "")

        app_search = AppSearch(
            ELASTICSEARCH_HOST,
            http_auth=ELASTICSEARCH_AUTH,
        )

        # GENES
        response_genes = app_search.search(
            engine_name="genes",
            body={
                "query": q_lucene,
                "page": {
                    "current": page_number,
                },
            },
        )
        pagination_genes = response_genes["meta"]["page"]
        context["num_genes"] = pagination_genes["total_results"]

        # CONDITIONS
        search_fields = [
            "name",
            "aliases_list_as_str",
            "doses_list_as_str",
            "tags_list_as_str",
        ]
        response_conditions = app_search.search(
            engine_name="conditiontypes",
            body={
                "query": q_lucene,
                "search_fields": {f: {} for f in search_fields},
                "page": {
                    "current": page_number,
                },
            },
        )
        pagination_conditions = response_conditions["meta"]["page"]
        context["num_conditions"] = pagination_conditions["total_results"]

        # PHENOTYPES
        if field == "tags":
            search_fields = ["tags_list_as_str"]
        else:
            search_fields = ["name", "description", "tags_list_as_str"]

        response_phenotypes = app_search.search(
            engine_name="observables",
            body={
                "query": q_lucene,
                "search_fields": {f: {} for f in search_fields},
                "page": {
                    "current": page_number,
                },
            },
        )

        pagination_phenotypes = response_phenotypes["meta"]["page"]
        context["num_phenotypes"] = pagination_phenotypes["total_results"]

        # DATASETS
        if field == "medium":
            search_fields = ["medium"]
        else:
            search_fields = [
                "id",
                "paper",
                "collection",
                "phenotype_aliases_list_as_str",
                "conditions_aliases_list_as_str",
                "medium",
                "conditionset",
                "phenotype",
                # "data_available",
                "tags_list_as_str",
            ]

        response_datasets = app_search.search(
            engine_name="datasets",
            body={
                "query": q_lucene,
                "search_fields": {f: {} for f in search_fields},
                "page": {
                    "current": page_number,
                },
            },
        )

        pagination_datasets = response_datasets["meta"]["page"]
        context["num_datasets"] = pagination_datasets["total_results"]

        # PAPERS
        response_papers = app_search.search(
            engine_name="papers",
            body={
                "query": q_lucene,
                "page": {
                    "current": page_number,
                },
            },
        )
        pagination_papers = response_papers["meta"]["page"]
        context["num_papers"] = pagination_papers["total_results"]

        # If no tab is specified, pick the one with the highest number of results
        if tab == "":
            num_results = {'genes': context['num_genes'],
                           'conditions': context['num_conditions'],
                           'phenotypes': context['num_phenotypes'],
                           'datasets': context['num_datasets'],
                           'papers': context['num_papers']}
            tab = max(num_results, key=(lambda key: num_results[key]))

        context["tab"] = tab

        if tab == "genes":
            search_fields = [
                "id",
                "systematic_name",
                "common_name",
                "aliases_list_as_str",
                "description",
            ]
            context["genes_page_obj"] = flatten_response(
                response_genes["results"], search_fields
            )
            [page_range, results_range] = get_page_range(page_number, pagination_genes)
            context["page_range"] = page_range
            context["results_range"] = results_range
            context["num_pages"] = pagination_genes["total_pages"]
        elif tab == "conditions":
            results_fields = [
                "id",
                "name",
                "aliases_list_as_str",
                "doses_list_as_str",
                "observables_list_as_str",
                "papers_list_as_str",
                "tags_list_as_str",
            ]
            context["conditions_page_obj"] = flatten_response(
                response_conditions["results"], results_fields
            )
            [page_range, results_range] = get_page_range(page_number, pagination_conditions)
            context["page_range"] = page_range
            context["results_range"] = results_range
            context["num_pages"] = pagination_conditions["total_pages"]
        elif tab == "phenotypes":
            results_fields = [
                "id",
                "name",
                "description",
                "phenotypes_list_as_str",
                "reporters_list_as_str",
                "conditiontypes_list_as_str",
                "papers_list_as_str",
                "tags_list_as_str",
            ]
            context["phenotypes_page_obj"] = flatten_response(
                response_phenotypes["results"], results_fields
            )
            [page_range, results_range] = get_page_range(page_number, pagination_phenotypes)
            context["page_range"] = page_range
            context["results_range"] = results_range
            context["num_pages"] = pagination_phenotypes["total_pages"]
        elif tab == "datasets":
            results_fields = [
                "id",
                "paper",
                "collection",
                "phenotype_aliases_list_as_str",
                "conditions_aliases_list_as_str",
                "medium",
                "conditionset",
                "phenotype",
                # "data_available",
                "tags_list_as_str",
            ]
            context["datasets_page_obj"] = flatten_response(
                response_datasets["results"], results_fields
            )
            [page_range, results_range] = get_page_range(page_number, pagination_datasets)
            context["page_range"] = page_range
            context["results_range"] = results_range
            context["num_pages"] = pagination_datasets["total_pages"]
        else:
            search_fields = [
                "id",
                "systematic_name",
                "pmid",
                "pub_date",
                "tags_list_as_str",
            ]
            context["papers_page_obj"] = flatten_response(
                response_papers["results"], search_fields
            )
            [page_range, results_range] = get_page_range(page_number, pagination_papers)
            context["page_range"] = page_range
            context["results_range"] = results_range
            context["num_pages"] = pagination_papers["total_pages"]

    else:
        form = GlobalSearchForm()
        context["form"] = form

    return render(request, "search/index.html", context)


def get_page_range(page_number, es_pagination):
    first_page = np.maximum(1, page_number - 3)
    last_page = np.minimum(es_pagination["total_pages"], page_number + 3)
    page_range = np.arange(first_page, last_page + 1)

    if es_pagination["total_results"] > 0:
        start_index = es_pagination["size"] * (page_number - 1) + 1
        end_index = np.minimum(
            es_pagination["total_results"], start_index + es_pagination["size"] - 1
        )
        results_range = "%d-%d of %d" % (
            start_index,
            end_index,
            es_pagination["total_results"],
        )
    else:
        results_range = "0"

    return page_range, results_range


def flatten_response(response, fields):
    flat_response = []
    for r in response:
        x = {}
        for f in fields:
            x[f] = r[f]["raw"]
            x[f] = int(x[f]) if f == "id" else x[f]
        flat_response.append(x)
    return flat_response
