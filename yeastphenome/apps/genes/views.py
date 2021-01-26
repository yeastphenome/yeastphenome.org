from django.shortcuts import render
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, reverse
from django.conf import settings
from django.db.models import Q
import pandas

from yeastphenome.apps.datasets.models import Data, Dataset
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

    # Get data for gene1 and gene2 as pandas dataframes
    data1 = pandas.DataFrame(list(Data.objects.filter(gene_id=gene1.id).values()))
    data2 = pandas.DataFrame(list(Data.objects.filter(gene_id=gene2.id).values()))

    # Join the 2 dataframes using dataset_id as the key
    data = data1.merge(data2, on="dataset_id")

    # Only keep rows where both genes have values (are not null)
    data = data.loc[data["valuez_x"].notnull() & data["valuez_y"].notnull()]

    # Get datasets names
    datasets = pandas.DataFrame(
        list(Dataset.objects.filter(id__in=data["dataset_id"].values).values())
    )

    # Add them to the data dataframe
    data = data.merge(datasets[["id", "name"]], left_on="dataset_id", right_on="id")

    # Convert to scores dictionary for view
    scores = data[["dataset_id", "valuez_x", "valuez_y", "name"]].to_dict(
        orient="index"
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
