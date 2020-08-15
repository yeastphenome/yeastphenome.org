from django.shortcuts import render, Http404

from ratelimit.decorators import ratelimit
from yeastphenome.apps.datasets.models import Dataset
from yeastphenome.apps.papers.models import Paper
from yeastphenome.apps.common.utils import (
    get_papers_by_year,
    get_collections_by_year,
)
from yeastphenome.apps.papers.utils import get_paper_references_context
from yeastphenome.settings import (
    VIEW_RATE_LIMIT as rl_rate,
    VIEW_RATE_LIMIT_BLOCK as rl_block,
)

# Visuals


@ratelimit(key="ip", rate=rl_rate, block=rl_block)
def paper_citation_graph(request, paper_id):
    """A citation graph that shows all of a paper's citations, and whether or
       not each outgoing citation is in the database
    """
    try:
        paper = Paper.objects.get(id=paper_id)
    except Paper.DoesNotExist:
        return Http404

    context = get_paper_references_context(paper)
    return render(request, "graphs/citation-graph-wrapper.html", context)


@ratelimit(key="ip", rate=rl_rate, block=rl_block)
def papers_by_year(request):
    """Render a chart.js visualization for papers by year. Color by year"""
    context = {"paper_counts": get_papers_by_year()}
    return render(request, "graphs/papers-by-year-wrapper.html", context)


@ratelimit(key="ip", rate=rl_rate, block=rl_block)
def collection_by_year(request, dataset_id):
    """Show change in time of collection associated with a dataset"""
    try:
        dataset = Dataset.objects.get(id=dataset_id)
    except Dataset.DoesNotExist:
        return Http404

    context = {
        "collection_yearly_counts": get_collections_by_year(dataset.collection),
        "collection": dataset.collection,
    }
    return render(request, "graphs/collection-by-year-wrapper.html", context)
