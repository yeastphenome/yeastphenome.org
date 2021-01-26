from django.shortcuts import render, redirect
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, reverse
from django.conf import settings
from django.contrib import messages
from django.db.models import Q

from yeastphenome.apps.datasets.models import Data
from yeastphenome.apps.genes.models import Gene, GeneSimilarity
from yeastphenome.apps.genes.search import get_search_tags
from ratelimit.decorators import ratelimit
from yeastphenome.settings import (
    VIEW_RATE_LIMIT as rl_rate,
    VIEW_RATE_LIMIT_BLOCK as rl_block,
)


# Explore by genes


@ratelimit(key="ip", rate=rl_rate, block=rl_block)
def gene_explorer(request):

    taglist = request.GET.get("query", "").split("|")

    links = [
        {"url": reverse("common:explorer"), "name": "Explore data"},
        {"url": reverse("genes:index"), "name": "Genes"},
    ]
    context = {
        "links": links,
        "active": "explorer",
        "tags": get_search_tags(),
        "taglist": taglist,
    }
    return render(request, "genes/index.html", context)


@ratelimit(key="ip", rate=rl_rate, block=rl_block)
def gene_detail(request, gene_id):

    gene = get_object_or_404(Gene, pk=gene_id)

    # Assemble links assuming on root of page
    links = [
        {"url": reverse("common:explorer"), "name": "Explore data"},
        {"url": reverse("genes:index"), "name": "Genes"},
        {"url": reverse("genes:detail", args=[gene.id]), "name": "%s" % gene},
    ]

    context = {"links": links, "active": "explorer", "gene": gene}

    # Get the top and bottom phenotypic scores
    context["datasets_top"] = gene.get_data(reverse=False)[:10]
    context["datasets_bottom"] = gene.get_data(reverse=True)[:10]

    # Get the top and bottom correlations
    context["sims_top"] = gene.get_ranked_similar(reverse=False)[:10]
    context["sims_bottom"] = gene.get_ranked_similar(reverse=True)[:10]

    context["links"] = links
    return render(request, "genes/detail.html", context)


@ratelimit(key="ip", rate=rl_rate, block=rl_block)
def similar_genes(request, gene_id):

    gene = get_object_or_404(Gene, pk=gene_id)

    sims = gene.get_ranked_similar(reverse=False).select_related("gene2")

    links = [
        {"url": reverse("common:explorer"), "name": "Explore data"},
        {"url": reverse("genes:index"), "name": "Genes"},
        {
            "url": reverse("genes:detail", args=[gene.id]),
            "name": "%s" % gene,
        },
        {
            "url": reverse("genes:similar_genes", args=[gene.id]),
            "name": "Similar Genes",
        },
    ]

    total_sims = sims.count()
    ranks = [(1 - (idx / total_sims)) * 100 for idx, sim in enumerate(sims)]
    context = {
        "gene": gene,
        "sims": sims,
        "ranks": ranks,
        "links": links,
        "active": "explorer",
    }
    return render(request, "genes/similar_genes.html", context)


@ratelimit(key="ip", rate=rl_rate, block=rl_block)
def similar_scatterplot(request, gene1_id, gene2_id):
    """Generate a scatterplot to compare two genes across datasets. You can
    interchange gene1 and gene2 and they will produce the same plot (but switched
    axes). This makes the view flexible to any combination of genes.
    """
    gene1 = get_object_or_404(Gene, pk=gene1_id)
    gene2 = get_object_or_404(Gene, pk=gene2_id)

    # Get the correlation to add
    sim = GeneSimilarity.objects.filter(
        Q(gene1=gene1, gene2=gene2) | Q(gene1=gene2, gene2=gene1)
    )

    # Explore data > Genes > YHR045 / YHR045W > Similar genes > DAP1 / YPL170W
    links = [
        {"url": reverse("common:explorer"), "name": "Explore data"},
        {"url": reverse("genes:index"), "name": "Genes"},
        {
            "url": reverse("genes:detail", args=[gene1.id]),
            "name": "%s" % gene1,
        },
        {
            "url": reverse("genes:similar_genes", args=[gene1.id]),
            "name": "Similar Genes",
        },
        {
            "url": reverse("genes:similar_scatterplot", args=[gene1.id, gene2.id]),
            "name": "%s" % gene2,
        },
    ]

    # But we want to sort the genes by id so we can correctly assign the axes
    # This means that gene1 should have the smaller id
    if gene1.id > gene2.id:
        gene1, gene2 = gene2, gene1
    names = {gene.id: str(gene) for gene in [gene1, gene2]}

    # We only want datasets with both genes defined
    datasets1 = gene1.data_set.filter(valuez__isnull=False).values_list(
        "dataset_id", flat=True
    )
    datasets2 = gene2.data_set.filter(valuez__isnull=False).values_list(
        "dataset_id", flat=True
    )
    shared = set(datasets1).intersection(set(datasets2))

    # Cut out early if there is no intersection
    if not shared:
        messages.info(request, "These datasets do not have any overlapping genes")
        return redirect("genes:detail", args=[gene1.id])

    # Get shared datasets, and create a lookup of scores based on dataset id
    data = Data.objects.filter(
        Q(dataset_id__in=shared), Q(gene_id__in=[gene1.id, gene2.id])
    )
    values = data.values_list("dataset_id", "gene_id", "valuez", "dataset__name")
    scores = {}

    # Lookup looks like  15343: {'values': [Decimal('-0.97599'), Decimal('0.34786')], 'genes': [1, 3]},
    # Note that the gene ids are sorted least to greatest, so gene1 < gene2
    for value in values:
        if value[0] not in scores:
            scores[value[0]] = {
                "values": [],
                "genes": [],
                "names": [],
                "dataset_name": value[3],
            }
        scores[value[0]]["values"].append(value[2])
        scores[value[0]]["genes"].append(value[1])
        scores[value[0]]["names"].append(names[value[1]])

    context = {
        "gene1": gene1,
        "gene2": gene2,
        "scores": scores,
        "sim": sim.first(),
        "links": links,
        "active": "explorer",
    }
    return render(request, "genes/similar_scatterplot.html", context)


@ratelimit(key="ip", rate=rl_rate, block=rl_block)
def gene_datasets(request, gene_id):
    import numpy as np

    gene = get_object_or_404(Gene, pk=gene_id)

    links = [
        {"url": reverse("common:explorer"), "name": "Explore data"},
        {"url": reverse("genes:index"), "name": "Genes"},
        {
            "url": reverse("genes:detail", args=[gene.id]),
            "name": "%s" % gene,
        },
        {
            "url": reverse("genes:datasets", args=[gene.id]),
            "name": "Phenotypic Scores",
        },
    ]

    # Derive datasets bins here
    datapoints = gene.get_data().values_list("valuez")

    count, division = np.histogram([float(x[0]) for x in datapoints])
    counts = []
    for i, number in enumerate(count):
        counts.append({"count": number, "value": division[i + 1]})

    context = {
        "gene": gene,
        "links": links,
        "active": "explorer",
        "counts": counts,
        "division": division,
    }

    return render(request, "genes/gene_datasets.html", context)


@ratelimit(key="ip", rate=rl_rate, block=rl_block)
def download_gene_similarities(request, gene_id):
    """Download all GeneSimilarity values for a given gene"""

    import pandas as pd

    gene = get_object_or_404(Gene, pk=gene_id)

    sims = (
        gene.get_ranked_similar()
        .select_related("gene1__systematic_name", "gene2__systematic_name")
        .values_list(
            "gene1__systematic_name", "gene2__systematic_name", "score", "pvalue"
        )
    )

    df = pd.DataFrame(sims)
    df.columns = ["Gene1", "Gene2", "Correlation mean", "Correlation std. dev."]

    filename = "%s_gene_similarities_%s.txt" % (
        settings.DOWNLOAD_PREFIX,
        gene.systematic_name,
    )

    # Prepare the HttpResponse
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = "attachment; filename=%s" % filename

    # Print data matrix to response buffer
    df.to_csv(path_or_buf=response, sep="\t", index=False)

    return response


@ratelimit(key="ip", rate=rl_rate, block=rl_block)
def download_gene_scores(request, gene_id=None):
    """Download all datasets. If a gene name is provided, filter to those"""

    import pandas as pd

    gene = get_object_or_404(Gene, pk=gene_id)

    scores = (
        gene.get_data()
        .select_related("dataset__name")
        .values_list("dataset__name", "valuez")
    )
    scores_df = pd.DataFrame(
        scores, columns=["Dataset name", "Normalized Phenotypic Score"]
    )
    scores_df["Gene"] = gene.systematic_name
    scores_df = scores_df.reindex(
        columns=["Gene", "Dataset name", "Normalized Phenotypic Score"]
    )

    # Prepare the HttpResponse
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="%s_%s_scores.txt"' % (
        settings.DOWNLOAD_PREFIX,
        gene.systematic_name,
    )

    # Print data matrix to response buffer
    scores_df.to_csv(path_or_buf=response, sep="\t", index=False)

    return response
