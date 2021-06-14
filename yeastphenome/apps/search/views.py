from django.views.decorators.cache import never_cache
from django.shortcuts import render

from elastic_enterprise_search import AppSearch

from yeastphenome.apps.common.forms import GlobalSearchForm

from ratelimit.decorators import ratelimit
from yeastphenome.settings import (
    VIEW_RATE_LIMIT as rl_rate,
    VIEW_RATE_LIMIT_BLOCK as rl_block,
    ELASTICSEARCH_HOST,
    ELASTICSEARCH_AUTH
)

import numpy as np
import re


@never_cache
@ratelimit(key="ip", rate=rl_rate, block=rl_block)
def index2(request):

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
        tab = request.GET.get("tab", "papers")
        if tab == "":
            tab = "papers"
        context["tab"] = tab

        app_search = AppSearch(
            ELASTICSEARCH_HOST,
            http_auth=ELASTICSEARCH_AUTH,
        )

        # GENES

        search_fields = ["id",
                         "systematic_name",
                         "common_name",
                         "aliases_list_as_str",
                         "description"]

        response = app_search.search(
            engine_name="genes",
            body={
                "query": q_lucene,
                "page": {
                    "current": page_number,
                }
            }
        )
        pagination = response["meta"]["page"]
        context["num_genes"] = pagination["total_results"]
        if tab == "genes":
            context["genes_page_obj"] = flatten_response(response["results"], search_fields)
            [page_range, results_range] = get_page_range(page_number, pagination)
            context["page_range"] = page_range
            context["results_range"] = results_range
            context["num_pages"] = pagination["total_pages"]

        # CONDITIONS

        results_fields = ["id",
                          "name",
                          "aliases_list_as_str",
                          "doses_list_as_str",
                          "observables_list_as_str",
                          "papers_list_as_str",
                          "tags_list_as_str"]
        search_fields = ["name",
                         "aliases_list_as_str",
                         "doses_list_as_str",
                         "tags_list_as_str"]
        response = app_search.search(
            engine_name="conditiontypes",
            body={
                "query": q_lucene,
                "search_fields": {f: {} for f in search_fields},
                "page": {
                    "current": page_number,
                }
            }
        )
        pagination = response["meta"]["page"]
        context["num_conditions"] = pagination["total_results"]
        if tab == "conditions":
            context["conditions_page_obj"] = flatten_response(response["results"], results_fields)
            [page_range, results_range] = get_page_range(page_number, pagination)
            context["page_range"] = page_range
            context["results_range"] = results_range
            context["num_pages"] = pagination["total_pages"]

        # PHENOTYPES

        if field == 'tags':
            search_fields = ["tags_list_as_str"]
        else:
            search_fields = ["name",
                             "description",
                             "tags_list_as_str"]

        results_fields = ["id",
                          "name",
                          "description",
                          "phenotypes_list_as_str",
                          "reporters_list_as_str",
                          "conditiontypes_list_as_str",
                          "papers_list_as_str",
                          "tags_list_as_str"]

        response = app_search.search(
            engine_name="observables",
            body={
                "query": q_lucene,
                "search_fields": {f: {} for f in search_fields},
                "page": {
                    "current": page_number,
                }
            }
        )

        pagination = response["meta"]["page"]
        context["num_phenotypes"] = pagination["total_results"]
        if tab == "phenotypes":
            context["phenotypes_page_obj"] = flatten_response(response["results"], results_fields)
            [page_range, results_range] = get_page_range(page_number, pagination)
            context["page_range"] = page_range
            context["results_range"] = results_range
            context["num_pages"] = pagination["total_pages"]

        # DATASETS

        if field == 'medium':
            search_fields = ["medium"]
        else:
            search_fields = ["id",
                             "paper",
                             "collection",
                             "phenotype_aliases_list_as_str",
                             "conditions_aliases_list_as_str",
                             "medium",
                             "conditionset",
                             "phenotype",
                             # "data_available",
                             "tags_list_as_str"]

        results_fields = ["id",
                          "paper",
                          "collection",
                          "phenotype_aliases_list_as_str",
                          "conditions_aliases_list_as_str",
                          "medium",
                          "conditionset",
                          "phenotype",
                          # "data_available",
                          "tags_list_as_str"]

        response = app_search.search(
            engine_name="datasets",
            body={
                "query": q_lucene,
                "search_fields": {f: {} for f in search_fields},
                "page": {
                    "current": page_number,
                }
            }
        )

        pagination = response["meta"]["page"]
        context["num_datasets"] = pagination["total_results"]
        if tab == "datasets":
            context["datasets_page_obj"] = flatten_response(response["results"], results_fields)
            [page_range, results_range] = get_page_range(page_number, pagination)
            context["page_range"] = page_range
            context["results_range"] = results_range
            context["num_pages"] = pagination["total_pages"]


        # PAPERS

        search_fields = ["id",
                         "systematic_name",
                         "pmid",
                         "pub_date",
                         "tags_list_as_str"]

        response = app_search.search(
            engine_name="papers",
            body={
                "query": q_lucene,
                "page": {
                    "current": page_number,
                }
            }
        )

        pagination = response["meta"]["page"]
        context["num_papers"] = pagination["total_results"]
        if tab == "papers":
            context["papers_page_obj"] = flatten_response(response["results"], search_fields)
            [page_range, results_range] = get_page_range(page_number, pagination)
            context["page_range"] = page_range
            context["results_range"] = results_range
            context["num_pages"] = pagination["total_pages"]

    else:
        form = GlobalSearchForm()
        context["form"] = form

    return render(request, "search/index.html", context)


def get_page_range(page_number, es_pagination):
    first_page = np.maximum(1, page_number-3)
    last_page = np.minimum(es_pagination["total_pages"], page_number+3)
    page_range = np.arange(first_page, last_page+1)

    if es_pagination["total_results"] > 0:
        start_index = es_pagination["size"] * (page_number - 1) + 1
        end_index = np.minimum(es_pagination["total_results"], start_index + es_pagination["size"] - 1)
        results_range = '%d-%d of %d' % (start_index, end_index, es_pagination["total_results"])
    else:
        results_range = '0'

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

