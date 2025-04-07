from django.views.decorators.cache import never_cache
from django.shortcuts import render

from elasticsearch import Elasticsearch

from yeastphenome.apps.common.forms import GlobalSearchForm
from yeastphenome.settings import (
    ELASTICSEARCH_CLOUD_ID,
    ELASTICSEARCH_USERNAME,
    ELASTICSEARCH_PASSWORD
)

import re
import numpy as np
import unicodedata
from typing import Tuple, List, Set


from yeastphenome.apps.papers.search import (
    index_name as index_name_papers,
    query_fields as query_fields_papers, 
    result_fields as result_fields_papers,
    field_aliases as field_aliases_papers
)
from yeastphenome.apps.genes.search import (
    index_name as index_name_genes,
    query_fields as query_fields_genes,
    result_fields as result_fields_genes,
    field_aliases as field_aliases_genes
)
from yeastphenome.apps.conditions.search import (
    index_name as index_name_conditions,
    query_fields as query_fields_conditions,
    result_fields as result_fields_conditions,
    field_aliases as field_aliases_conditions
)
from yeastphenome.apps.phenotypes.search import (
    index_name as index_name_phenotypes,
    query_fields as query_fields_phenotypes,
    result_fields as result_fields_phenotypes,
    field_aliases as field_aliases_phenotypes
)
from yeastphenome.apps.datasets.search import (
    index_name as index_name_datasets,
    query_fields as query_fields_datasets,
    result_fields as result_fields_datasets,
    field_aliases as field_aliases_datasets
)


@never_cache
def search_index_view(request):

    context = dict()

    if "q" in request.GET:
        
        # Get the user-provided query
        form = GlobalSearchForm(request.GET)

        if form.is_valid():
            query = form.cleaned_data["q"]
        else:
            query = request.GET.get("q")

        # Get the number of the results page to display, if any
        current_page = int(request.GET.get("page", "1"))
        results_per_page = 10
        start_index = (current_page  - 1) * results_per_page

        # Get the section of the results to display, if any
        active_tab = request.GET.get("tab", "")

        # Create client with cloud deployment
        es = Elasticsearch(
            cloud_id=ELASTICSEARCH_CLOUD_ID,
            basic_auth=(ELASTICSEARCH_USERNAME, ELASTICSEARCH_PASSWORD)
        )

        elasticsearch_indices = {
            "papers": index_name_papers,
            "genes": index_name_genes,
            "conditions": index_name_conditions,
            "phenotypes": index_name_phenotypes,
            "datasets": index_name_datasets,
            }
        
        field_aliases = {
            "papers": field_aliases_papers,
            "genes": field_aliases_genes,
            "conditions": field_aliases_conditions,
            "phenotypes": field_aliases_phenotypes,
            "datasets": field_aliases_datasets,
        }
        
        query_fields = {
            "papers": query_fields_papers,
            "genes": query_fields_genes,
            "conditions": query_fields_conditions,
            "phenotypes": query_fields_phenotypes,
            "datasets": query_fields_datasets,
            }
        
        result_fields = {
            "papers": result_fields_papers,
            "genes": result_fields_genes,
            "conditions": result_fields_conditions,
            "phenotypes": result_fields_phenotypes,
            "datasets": result_fields_datasets,
            }
    
        
        def execute_elasticsearch_query(engine):

            valid_fields = list(field_aliases[engine].keys())
            cleaned_query, search_fields = parse_query_fields(query, valid_fields)

            if not search_fields:
                # If no specific fields are provided, use all valid fields
                search_fields = query_fields[engine]
            else:
                # Map the field aliases to the actual field names
                search_fields = [field_aliases[engine][field] for field in search_fields if field in field_aliases[engine]]

            body = {
                "query": {
                    "simple_query_string": {
                        "query": cleaned_query,
                        "fields": search_fields,
                        "default_operator": "AND",
                        }
                    },
                "from": start_index,
                "size": results_per_page,
            }

            response = es.search(index=elasticsearch_indices[engine], body=body)
            
            return response
        
        # GENES: perform the search and handle the results
        genes_search_response = execute_elasticsearch_query("genes")
        total_results = genes_search_response["hits"]["total"]["value"]
        context["num_genes"] = total_results

        # CONDITIONS: perform the search and handle the results
        conditions_search_response = execute_elasticsearch_query("conditions")
        total_results = conditions_search_response["hits"]["total"]["value"]
        context["num_conditions"] = total_results

        # PHENOTYPES: perform the search and handle the results
        phenotypes_search_response = execute_elasticsearch_query("phenotypes")
        total_results = phenotypes_search_response["hits"]["total"]["value"]
        context["num_phenotypes"] = total_results

        # DATASETS: perform the search and handle the results
        datasets_search_response = execute_elasticsearch_query("datasets")
        total_results = datasets_search_response["hits"]["total"]["value"]
        context["num_datasets"] = total_results

        # PAPERS: perform the search and handle the results
        papers_search_response = execute_elasticsearch_query("papers")
        total_results = papers_search_response["hits"]["total"]["value"]
        context["num_papers"] = total_results

        # If no tab is provided, set the default tab to the one with the most results
        if active_tab == "":
            num_results = {
                "genes": context["num_genes"],
                "conditions": context["num_conditions"],
                "phenotypes": context["num_phenotypes"],
                "screens": context["num_datasets"],
                "papers": context["num_papers"],
            }
            active_tab = max(num_results, key=(lambda key: num_results[key]))
        
        context["tab"] = active_tab
        
        if active_tab == "papers":

            results = [hit["_source"] for hit in papers_search_response["hits"]["hits"]]
            results = extract_result_fields(results, result_fields["papers"])

            total_pages = int(np.ceil(context["num_papers"]/results_per_page))
            [displayed_results_range, displayed_pagination_range] = get_pagination_info(papers_search_response, current_page, results_per_page)
            
            context["papers_results"] = results

        elif active_tab == "conditions":

            results = [hit["_source"] for hit in conditions_search_response["hits"]["hits"]]
            results = extract_result_fields(results, result_fields["conditions"])

            total_pages = int(np.ceil(context["num_conditions"]/results_per_page))
            [displayed_results_range, displayed_pagination_range] = get_pagination_info(conditions_search_response, current_page, results_per_page)

            context["conditions_results"] = results
        
        elif active_tab == "genes":

            results = [hit["_source"] for hit in genes_search_response["hits"]["hits"]]
            results = extract_result_fields(results, result_fields["genes"])

            total_pages = int(np.ceil(context["num_genes"]/results_per_page))
            [displayed_results_range, displayed_pagination_range] = get_pagination_info(genes_search_response, current_page, results_per_page)

            context["genes_results"] = results

        elif active_tab == "screens":  

            results = [hit["_source"] for hit in datasets_search_response["hits"]["hits"]]
            results = extract_result_fields(results, result_fields["datasets"])

            total_pages = int(np.ceil(context["num_datasets"]/results_per_page))
            [displayed_results_range, displayed_pagination_range] = get_pagination_info(datasets_search_response, current_page, results_per_page)

            context["datasets_results"] = results
            
        elif active_tab == "phenotypes":    
            
            results = [hit["_source"] for hit in phenotypes_search_response["hits"]["hits"]]
            results = extract_result_fields(results, result_fields["phenotypes"])

            total_pages = int(np.ceil(context["num_phenotypes"]/results_per_page))
            [displayed_results_range, displayed_pagination_range] = get_pagination_info(phenotypes_search_response, current_page, results_per_page)

            context["phenotypes_results"] = results
        
        context["num_pages"] = total_pages
        context["page_range"] = displayed_pagination_range
        context["results_range"] = displayed_results_range

    else:

        # If no query is provided, show the search form
        # and set the default tab to "papers"
        active_tab = "papers"
        context["tab"] = active_tab

        # Create a blank search form
        form = GlobalSearchForm()
        context["form"] = form

    return render(request, "search/index.html", context)


def clean_query_input(query: str) -> str:
    # Normalize unicode, strip extra whitespace
    query = unicodedata.normalize("NFKC", query)
    return query.strip()


def extract_result_fields(results, result_fields):
    trimmed_results = []
    for result in results:
        trimmed_result = {}
        for field in result_fields:
            if field in result.keys():
                trimmed_result[field] = result[field]
                trimmed_result[field] = int(trimmed_result[field]) if field == "id" else trimmed_result[field]
        trimmed_results.append(trimmed_result)
    return trimmed_results


def get_pagination_info(search_response, current_page, results_per_page):
    
    total_results = search_response["hits"]["total"]["value"]
    total_results_on_current_page = len(search_response["hits"]["hits"])

    # Calculate range of items shown
    if total_results == 0:
        displayed_results_range = "Showing 0 of 0 results"
    else:
        start_index = (current_page - 1) * results_per_page + 1
        end_index = start_index + total_results_on_current_page - 1
        displayed_results_range = f"Showing {start_index}–{end_index} of {total_results} results"

    # Calculate total pages
    total_pages = max(1, int(np.ceil(total_results/results_per_page)))

    # Calculate pagination range
    displayed_pagination_range = []
    for page in range(current_page - 1, current_page + 2):
        if 1 <= page <= total_pages:
            displayed_pagination_range.append(page)
    
    return displayed_results_range, displayed_pagination_range




def parse_query_fields(user_query: str, valid_fields: Set[str]) -> Tuple[str, List[str]]:
    """
    Parses the user query for field restrictions like `field:term`
    and returns:
      1. A cleaned query string with field names stripped.
      2. A list of valid fields extracted from the query.
    """
    pattern = re.compile(r'(?P<field>\w+):(?P<term>"[^"]+"|\S+)')
    used_fields = []
    terms = []
    last_end = 0

    for match in pattern.finditer(user_query):
        field = match.group("field")
        term = match.group("term")
        if field in valid_fields:
            used_fields.append(field)
            terms.append(term)
        else:
            # Keep unknown field queries as-is
            terms.append(match.group(0))
        last_end = match.end()

    # Add the remaining part of the query (if any)
    remaining_query = user_query[last_end:].strip()
    if remaining_query:
        terms.append(remaining_query)

    cleaned_query = " ".join(terms)
    cleaned_query = clean_query_input(cleaned_query)

    return cleaned_query, list(set(used_fields))


