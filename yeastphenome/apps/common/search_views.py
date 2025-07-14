from django.views.decorators.cache import never_cache
from django.shortcuts import render, reverse
from django.db.models import Q
from django.core.paginator import Paginator
from django.contrib.postgres.aggregates.general import StringAgg

from yeastphenome.apps.datasets.models import Dataset
from yeastphenome.apps.papers.models import Paper
from yeastphenome.apps.genes.models import Gene
from yeastphenome.apps.conditions.models import ConditionType
from yeastphenome.apps.phenotypes.models import Observable

from yeastphenome.apps.common.forms import GlobalSearchForm
from yeastphenome.apps.common.utils_format import truncated_list_as_str

from yeastphenome.settings import (
    VIEW_RATE_LIMIT as rl_rate,
    VIEW_RATE_LIMIT_BLOCK as rl_block,
)

import itertools


@never_cache
def index(request):

    context = dict()

    if "q" in request.GET:

        form = GlobalSearchForm(request.GET)

        if form.is_valid():
            q = form.cleaned_data["q"]
            q_list = q.split(",")
            q_list = [qi.strip() for qi in q_list]

            # Do the search

            page_number = int(request.GET.get("page", "1"))
            tab = request.GET.get("tab", "papers")
            if tab == "":
                tab = "papers"
            context["tab"] = tab

            # Conditions
            conditions = ConditionType.objects.all_valid()
            filter_list_qi = Q()
            for qi in q_list:
                filter_list_qi &= (
                    Q(name__icontains=qi)
                    | Q(other_names__icontains=qi)
                    | Q(chebi_name__icontains=qi)
                    | Q(pubchem_name__icontains=qi)
                    | Q(tags__name__icontains=qi)
                )
            conditions = conditions.filter(filter_list_qi)
            conditions_ids = list(
                conditions.values_list("id", flat=True).order_by().distinct()
            )
            context["num_conditions"] = len(conditions_ids)
            if tab == "conditions":
                conditions = conditions.distinct()
                conditions_page_obj, page_range = get_paginator(conditions, page_number)

                conditions = conditions_page_obj.object_list
                conditions = conditions.annotate(
                    condition_doses=StringAgg(
                        "conditions__dose",
                        delimiter="; ",
                        distinct=True,
                        ordering="conditions__dose",
                    )
                )

                agg_field1 = "conditions__conditionset__dataset__paper__systematic_name"
                agg_field2 = "conditions__medium__dataset__paper__systematic_name"
                conditions = conditions.annotate(
                    papers1=StringAgg(agg_field1, delimiter="; ", distinct=True)
                )
                conditions = conditions.annotate(
                    papers2=StringAgg(agg_field2, delimiter="; ", distinct=True)
                )

                agg_field1 = (
                    "conditions__conditionset__dataset__phenotype__observable__name"
                )
                agg_field2 = "conditions__medium__dataset__phenotype__observable__name"
                conditions = conditions.annotate(
                    phenotypes1=StringAgg(agg_field1, delimiter="; ", distinct=True)
                )
                conditions = conditions.annotate(
                    phenotypes2=StringAgg(agg_field2, delimiter="; ", distinct=True)
                )

                conditions = conditions.annotate(
                    condition_tags=StringAgg(
                        "tags__name", delimiter="; ", distinct=True
                    )
                )

                conditions_page_values = list(
                    conditions.values(
                        "id",
                        "name",
                        "chebi_name",
                        "pubchem_name",
                        "condition_doses",
                        "papers1",
                        "papers2",
                        "phenotypes1",
                        "phenotypes2",
                        "condition_tags",
                    )
                )

                def merge_papers_phenotypes_names(condition_dict):
                    papers1 = condition_dict["papers1"].split("; ")
                    papers2 = condition_dict["papers2"].split("; ")
                    papers = list(itertools.chain.from_iterable([papers1, papers2]))
                    papers = [paper for paper in papers if not paper == ""]
                    papers = list(set(papers))
                    condition_dict["papers"] = truncated_list_as_str(papers, sort=True)

                    phenotypes1 = condition_dict["phenotypes1"].split("; ")
                    phenotypes2 = condition_dict["phenotypes2"].split("; ")
                    phenotypes = list(
                        itertools.chain.from_iterable([phenotypes1, phenotypes2])
                    )
                    phenotypes = [
                        phenotype for phenotype in phenotypes if not phenotype == ""
                    ]
                    phenotypes = list(set(phenotypes))
                    condition_dict["phenotypes"] = truncated_list_as_str(
                        phenotypes, sort=True
                    )

                    names = [
                        condition_dict["chebi_name"],
                        condition_dict["pubchem_name"],
                    ]
                    names = [
                        name for name in names if not name == "" and name is not None
                    ]
                    condition_dict["other_names"] = "; ".join(names)

                    return condition_dict

                conditions_page_values = [
                    merge_papers_phenotypes_names(paper_dict)
                    for paper_dict in conditions_page_values
                ]

                context["conditions_page_obj"] = conditions_page_values
                context["page_range"] = page_range

            # Phenotypes
            phenotypes = Observable.objects.all_valid()
            filter_list_qi = Q()
            for qi in q_list:
                filter_list_qi &= (
                    Q(name__icontains=qi)
                    | Q(phenotype__name__icontains=qi)
                    | Q(phenotype__reporter__icontains=qi)
                    | Q(tags__name__icontains=qi)
                )
            phenotypes = phenotypes.filter(filter_list_qi)
            phenotypes_ids = list(
                phenotypes.values_list("id", flat=True).order_by().distinct()
            )
            context["num_phenotypes"] = len(phenotypes_ids)
            if tab == "phenotypes":
                phenotypes = phenotypes.distinct()
                phenotypes_page_obj, page_range = get_paginator(phenotypes, page_number)

                phenotypes_page = phenotypes_page_obj.object_list
                phenotypes_page = phenotypes_page.annotate(
                    reporters=StringAgg(
                        "phenotype__reporter",
                        delimiter="; ",
                        distinct=True,
                        ordering="phenotype__reporter",
                    )
                )
                phenotypes_page = phenotypes_page.annotate(
                    agg_tags=StringAgg(
                        "tags__name",
                        delimiter="; ",
                        distinct=True,
                        ordering="tags__name",
                    )
                )
                agg_field = "phenotype__dataset__paper__systematic_name"
                phenotypes_page = phenotypes_page.annotate(
                    agg_papers=StringAgg(
                        agg_field, delimiter="; ", distinct=True, ordering=agg_field
                    )
                )
                agg_field = "phenotype__dataset__conditionset__conditions__type__name"
                phenotypes_page = phenotypes_page.annotate(
                    agg_conditions=StringAgg(
                        agg_field, delimiter="; ", distinct=True, ordering=agg_field
                    )
                )
                phenotypes_page_values = list(
                    phenotypes_page.values(
                        "id",
                        "name",
                        "reporters",
                        "agg_papers",
                        "agg_conditions",
                        "agg_tags",
                    )
                )
                context["phenotypes_page_obj"] = phenotypes_page_values
                context["page_range"] = page_range

            # Genes
            genes = Gene.objects.all_valid()
            filter_list_qi = Q()
            for qi in q_list:
                filter_list_qi &= (
                    Q(systematic_name__icontains=qi)
                    | Q(common_name__icontains=qi)
                    | Q(primary_sgdid__icontains=qi)
                    | Q(aliases__name__icontains=qi)
                    | Q(description__icontains=qi)
                )
            genes = genes.filter(filter_list_qi)
            if tab != "genes":
                # Quick way to get the number
                genes_ids = genes.values_list("id", flat=True).order_by().distinct()
                context["num_genes"] = genes_ids.count()
            else:
                genes = genes.distinct()
                genes = genes.annotate(
                    gene_aliases=StringAgg(
                        "aliases__name", delimiter="; ", distinct=True
                    )
                )
                genes_page_obj, page_range = get_paginator(genes, page_number)
                genes_page_obj_values = list(
                    genes_page_obj.object_list.values(
                        "id",
                        "systematic_name",
                        "common_name",
                        "gene_aliases",
                        "description",
                    )
                )
                context["num_genes"] = genes.count()
                context["genes_page_obj"] = genes_page_obj_values
                context["page_range"] = page_range

            # Datasets
            datasets = Dataset.objects.all_valid()
            filter_list_qi = Q()
            for qi in q_list:
                filter_list_qi &= (
                    Q(name__icontains=qi)
                    | Q(tags__name__icontains=qi)
                    | Q(phenotype__name__icontains=qi)
                    | Q(phenotype__reporter__icontains=qi)
                    | Q(phenotype__observable__name__icontains=qi)
                    | Q(phenotype__observable__tags__name__icontains=qi)
                    | Q(conditionset__conditions__type__name__icontains=qi)
                    | Q(conditionset__conditions__type__other_names__icontains=qi)
                    | Q(conditionset__conditions__type__chebi_name__icontains=qi)
                    | Q(conditionset__conditions__type__pubchem_name__icontains=qi)
                    | Q(conditionset__conditions__type__tags__name__icontains=qi)
                )
            filter_list = filter_list_qi | Q(
                medium__conditions__type__in=conditions_ids
            )
            # filter_list |= Q(medium__conditions__type__in=conditions_ids)
            # filter_list |= Q(phenotype__observable__in=phenotypes_ids)
            datasets = datasets.filter(filter_list)
            datasets_ids = list(
                datasets.values_list("id", flat=True).order_by().distinct()
            )
            context["num_datasets"] = len(datasets_ids)
            if tab == "datasets":
                datasets = datasets.distinct()
                datasets_page_obj, page_range = get_paginator(datasets, page_number)
                datasets_page_obj_values = list(
                    datasets_page_obj.object_list.values(
                        "id",
                        "paper__systematic_name",
                        "phenotype__name",
                        "conditionset__display_name",
                        "medium__display_name",
                        "collection__shortname",
                        "data_available__name",
                    )
                )
                context["datasets_page_obj"] = datasets_page_obj_values
                context["page_range"] = page_range

            # Papers
            papers = Paper.objects.all_valid()
            filter_list = Q()
            for qi in q_list:
                filter_list &= Q(systematic_name__icontains=qi)
            papers = papers.filter(filter_list)
            papers_values1 = list(papers.values_list("id", flat=True))
            papers_values2 = list(datasets.values_list("paper_id", flat=True))
            papers_values = list(set(papers_values1 + papers_values2))
            context["num_papers"] = len(papers_values)

            papers = Paper.objects.filter(id__in=papers_values)

            if tab == "papers":
                papers_page_obj, page_range = get_paginator(papers, page_number)
                papers_page_values = list(
                    papers_page_obj.object_list.values(
                        "id",
                        "systematic_name",
                        "observables_summary",
                        "conditiontypes_summary",
                    )
                )
                context["papers_page_obj"] = papers_page_values
                context["page_range"] = page_range

        context["form"] = form

    else:
        form = GlobalSearchForm()
        context["form"] = form

    context["active"] = "explorer"
    context["links"] = [
        {"url": reverse("common:search"), "name": "Search"},
    ]

    return render(request, "search/index.html", context)


def get_paginator(queryset, page_number):
    paginator = Paginator(queryset, 10)
    page_obj = paginator.get_page(page_number)
    num_pages = paginator.num_pages

    if num_pages <= 11 or page_number <= 6:
        page_range = [x for x in range(1, min(num_pages + 1, 12))]
    elif page_number > num_pages - 6:
        page_range = [x for x in range(num_pages - 10, num_pages + 1)]
    else:
        page_range = [x for x in range(page_number - 5, page_number + 6)]

    return page_obj, page_range
