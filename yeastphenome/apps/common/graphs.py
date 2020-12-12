from django.shortcuts import render, get_object_or_404

from ratelimit.decorators import ratelimit
from yeastphenome.apps.datasets.models import Dataset
from yeastphenome.apps.papers.models import Paper
from yeastphenome.apps.common.utils import (
    get_dataset_sources,
    get_dataset_genes,
    get_papers_by_year,
    get_collections_by_year,
    get_phenotype_measurements,
)
from yeastphenome.apps.papers.utils import get_paper_references_context
from yeastphenome.settings import (
    VIEW_RATE_LIMIT as rl_rate,
    VIEW_RATE_LIMIT_BLOCK as rl_block,
)

# Visuals


@ratelimit(key="ip", rate=rl_rate, block=rl_block)
def papers_citation_graph(request):
    return render(request, "graphs/citation-graph-springy-wrapper.html")


@ratelimit(key="ip", rate=rl_rate, block=rl_block)
def paper_citation_graph_explorable(request):
    """An explorable citation graph that starts with one of a set of known
    papers, and goes from there.
    NOT CURRENTLY IN USE - needs to be refactored
    """
    paper = Paper.objects.get(id=2)
    context = get_paper_references_context(paper)
    return render(request, "graphs/citation-graph-explorable-wrapper.html", context)


# ------------------------------------------------------------------------------

# Papers


@ratelimit(key="ip", rate=rl_rate, block=rl_block)
def paper_citation_graph(request, paper_id):
    """A citation graph that shows all of a paper's citations, and whether or
    not each outgoing citation is in the database
    """
    paper = get_object_or_404(Paper, pk=paper_id)
    context = get_paper_references_context(paper)
    return render(request, "graphs/citation-graph-wrapper.html", context)


@ratelimit(key="ip", rate=rl_rate, block=rl_block)
def papers_by_year(request):
    """Render a chart.js visualization for papers by year. Color by year"""
    context = {"paper_counts": get_papers_by_year()}
    return render(request, "graphs/papers-by-year-wrapper.html", context)


# Collections


@ratelimit(key="ip", rate=rl_rate, block=rl_block)
def collection_by_year(request, dataset_id):
    """Show change in time of collection associated with a dataset"""
    dataset = get_object_or_404(Dataset, pk=dataset_id)
    context = {
        "collection_yearly_counts": get_collections_by_year(dataset.collection),
        "collection": dataset.collection,
    }
    return render(request, "graphs/collection-by-year-wrapper.html", context)


# Phenotypes


@ratelimit(key="ip", rate=rl_rate, block=rl_block)
def phenotype_measurements(request):
    """Render a chart.js visualization for phenotypes broken down by measurement type"""
    return render(
        request,
        "graphs/phenotype-measurements-wrapper.html",
        get_phenotype_measurements(),
    )


# Datasets


@ratelimit(key="ip", rate=rl_rate, block=rl_block)
def dataset_sources(request):
    """Render a chart.js visualization for datastes broken down by sources"""
    return render(
        request,
        "graphs/dataset-sources-wrapper.html",
        get_dataset_sources(),
    )


@ratelimit(key="ip", rate=rl_rate, block=rl_block)
def dataset_genes(request, dataset_id=None):
    """A scrollable, searchable gene view of a dataset"""
    # Selects random dataset id if not defined
    return render(
        request, "graphs/dataset-genes-wrapper.html", get_dataset_genes(dataset_id)
    )
