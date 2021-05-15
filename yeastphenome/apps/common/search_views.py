from django.views.decorators.cache import never_cache
from django.shortcuts import render
from django.db.models import Q
from django.core.paginator import Paginator

from yeastphenome.apps.datasets.models import Dataset
from yeastphenome.apps.papers.models import Paper
from yeastphenome.apps.genes.models import Gene, GeneAlias
from yeastphenome.apps.conditions.models import ConditionType, Medium
from yeastphenome.apps.phenotypes.models import Observable, Phenotype

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

    if 'q' in request.GET:
        form = GlobalSearchForm(request.GET)
        if form.is_valid():
            q = form.cleaned_data['q']
            # Do the search

            page_number = request.GET.get('page')

            # Conditions
            conditions = ConditionType.objects.filter(Q(name__icontains=q) |
                                                      Q(other_names__icontains=q) |
                                                      Q(chebi_name__icontains=q) |
                                                      Q(pubchem_name__icontains=q) |
                                                      Q(tags__name__icontains=q)).distinct()
            context['conditions'] = conditions
            context['num_conditions'] = conditions.count()
            conditions_paginator = Paginator(conditions, 10)
            conditions_page_obj = conditions_paginator.get_page(page_number)
            context['conditions_page_obj'] = conditions_page_obj

            # Phenotypes
            phenotypes = Observable.objects.filter(Q(name__icontains=q) |
                                                   Q(description__icontains=q) |
                                                   Q(tags__name__icontains=q)).distinct()
            context['phenotypes'] = phenotypes
            context['num_phenotypes'] = phenotypes.count()
            phenotypes_paginator = Paginator(phenotypes, 10)
            phenotypes_page_obj = phenotypes_paginator.get_page(page_number)
            context['phenotypes_page_obj'] = phenotypes_page_obj

            # Genes
            genes = Gene.objects.filter(Q(systematic_name__icontains=q) |
                                        Q(common_name__icontains=q) |
                                        Q(primary_sgdid__icontains=q) |
                                        Q(aliases__name__icontains=q) |
                                        Q(description__icontains=q)).distinct()
            context['genes'] = genes
            context['num_genes'] = genes.count()
            genes_paginator = Paginator(genes, 10)
            genes_page_obj = genes_paginator.get_page(page_number)
            context['genes_page_obj'] = genes_page_obj

            # Datasets
            datasets = Dataset.objects.filter(Q(name__icontains=q) |
                                              Q(conditionset__conditions__type__in=conditions.values_list('id')) |
                                              Q(medium__conditions__type__in=conditions.values_list('id')) |
                                              Q(phenotype__observable__in=phenotypes.values_list('id')) |
                                              Q(tags__name__icontains=q)).distinct()
            context['datasets'] = datasets
            context['num_datasets'] = datasets.count()
            datasets_paginator = Paginator(datasets, 10)
            datasets_page_obj = datasets_paginator.get_page(page_number)
            context['datasets_page_obj'] = datasets_page_obj

            # Papers
            papers = Paper.objects.filter(Q(first_author__icontains=q) |
                                          Q(last_author__icontains=q) |
                                          Q(datasets__in=datasets.values_list('id'))).distinct()
            context['papers'] = papers
            context['num_papers'] = papers.count()
            papers_paginator = Paginator(papers, 10)
            papers_page_obj = papers_paginator.get_page(page_number)
            context['papers_page_obj'] = papers_page_obj

        context['form'] = form
    else:
        form = GlobalSearchForm()
        context['form'] = form

    # Select a random graph to add to the context
    return render(request, "search/index.html", context)
