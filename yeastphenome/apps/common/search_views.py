from django.views.decorators.cache import never_cache
from django.shortcuts import render
from django.db.models import Q
from django.core.paginator import Paginator

from yeastphenome.apps.datasets.models import Dataset
from yeastphenome.apps.papers.models import Paper
from yeastphenome.apps.genes.models import Gene
from yeastphenome.apps.conditions.models import ConditionType
from yeastphenome.apps.phenotypes.models import Observable

from yeastphenome.apps.common.forms import GlobalSearchForm

from ratelimit.decorators import ratelimit
from yeastphenome.settings import (
    VIEW_RATE_LIMIT as rl_rate,
    VIEW_RATE_LIMIT_BLOCK as rl_block,
)


@never_cache
@ratelimit(key="ip", rate=rl_rate, block=rl_block)
def index(request):

    context = dict()

    if "q" in request.GET:
        form = GlobalSearchForm(request.GET)
        if form.is_valid():
            q = form.cleaned_data["q"]
            q_list = q.split(" ")

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
                filter_list_qi &= (Q(name__icontains=qi)
                                   | Q(other_names__icontains=qi)
                                   | Q(chebi_name__icontains=qi)
                                   | Q(pubchem_name__icontains=qi)
                                   | Q(tags__name__icontains=qi))
            conditions = conditions.filter(filter_list_qi).distinct()
            context["num_conditions"] = conditions.count()
            if tab == "conditions":
                conditions_page_obj, page_range = get_paginator(conditions, page_number)
                context["conditions_page_obj"] = conditions_page_obj
                context["page_range"] = page_range

            # Phenotypes
            phenotypes = Observable.objects.all_valid()
            filter_list_qi = Q()
            for qi in q_list:
                filter_list_qi &= (Q(name__icontains=qi)
                                   | Q(phenotype__name__icontains=qi)
                                   | Q(phenotype__reporter__icontains=qi)
                                   | Q(tags__name__icontains=qi))
            phenotypes = phenotypes.filter(filter_list_qi).distinct()
            context["num_phenotypes"] = phenotypes.count()
            if tab == "phenotypes":
                phenotypes_page_obj, page_range = get_paginator(phenotypes, page_number)
                context["phenotypes_page_obj"] = phenotypes_page_obj
                context["page_range"] = page_range

            # Genes
            genes = Gene.objects.all_valid()
            filter_list_qi = Q()
            for qi in q_list:
                filter_list_qi &= (Q(systematic_name__icontains=qi)
                                   | Q(common_name__icontains=qi)
                                   | Q(primary_sgdid__icontains=qi)
                                   | Q(aliases__name__icontains=qi)
                                   | Q(description__icontains=qi))
            genes = genes.filter(filter_list_qi).distinct()
            context["num_genes"] = genes.count()
            if tab == "genes":
                genes_page_obj, page_range = get_paginator(genes, page_number)
                context["genes_page_obj"] = genes_page_obj
                context["page_range"] = page_range

            # Datasets
            datasets = Dataset.objects.all_valid()
            filter_list_qi = Q()
            for qi in q_list:
                filter_list_qi &= (Q(name__icontains=qi)
                                   | Q(tags__name__icontains=qi)
                                   | Q(phenotype__name__icontains=qi)
                                   | Q(phenotype__reporter__icontains=qi)
                                   | Q(phenotype__observable__name__icontains=qi)
                                   | Q(phenotype__observable__tags__name__icontains=qi))
            filter_list = filter_list_qi | Q(conditionset__conditions__type__in=conditions.values_list("id"))
            filter_list |= Q(medium__conditions__type__in=conditions.values_list("id"))
            datasets = datasets.filter(filter_list).distinct()
            context["num_datasets"] = datasets.count()
            if tab == "datasets":
                datasets_page_obj, page_range = get_paginator(datasets, page_number)
                context["datasets_page_obj"] = datasets_page_obj
                context["page_range"] = page_range

            # Papers
            papers = Paper.objects.all_valid()
            filter_list_qi = Q()
            for qi in q_list:
                filter_list_qi &= (Q(first_author__icontains=qi) | Q(last_author__icontains=qi))
            filter_list = filter_list_qi | Q(datasets__in=datasets.values_list("id"))
            papers = papers.filter(filter_list).distinct()
            context["num_papers"] = papers.count()
            if tab == "papers":
                papers_page_obj, page_range = get_paginator(papers, page_number)
                context["papers_page_obj"] = papers_page_obj
                context["page_range"] = page_range

        context["form"] = form

    else:
        form = GlobalSearchForm()
        context["form"] = form

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
