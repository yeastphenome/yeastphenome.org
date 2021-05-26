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

import numpy as np


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
    scores_lowest = gene.get_scores(ascending=True)[:10]
    scores_highest = gene.get_scores(ascending=False)[:10]
    similarities_lowest = gene.get_similarities(ascending=True)[:10]
    similarities_highest = gene.get_similarities(ascending=False)[:10]

    # Assemble links assuming on root of page
    links = [
        {"url": reverse("common:explorer"), "name": "Explore data"},
        {"url": reverse("genes:index"), "name": "Genes"},
        {"url": reverse("genes:detail", args=[gene.id]), "name": "%s" % gene},
    ]

    context = {
        "gene": gene,
        "scores_lowest": scores_lowest,
        "scores_highest": scores_highest,
        "similarities_lowest": similarities_lowest,
        "similarities_highest": similarities_highest,
        "links": links,
        "active": "explorer",
    }

    return render(request, "genes/detail_min.html", context)


@ratelimit(key="ip", rate=rl_rate, block=rl_block)
def scores(request, gene_id):

    gene = get_object_or_404(Gene, pk=gene_id)
    scores = gene.get_scores(ascending=True)

    links = [
        {"url": reverse("common:explorer"), "name": "Explore data"},
        {"url": reverse("genes:index"), "name": "Genes"},
        {
            "url": reverse("genes:detail", args=[gene.id]),
            "name": "%s" % gene,
        },
        {
            "url": reverse("genes:scores", args=[gene.id]),
            "name": "Phenotypic Scores",
        },
    ]

    context = {
        "gene": gene,
        "scores": scores,
        "links": links,
        "active": "explorer"
    }

    return render(request, "genes/scores_min.html", context)


@ratelimit(key="ip", rate=rl_rate, block=rl_block)
def similarities(request, gene_id):

    gene = get_object_or_404(Gene, pk=gene_id)
    similarities = gene.get_similarities(ascending=False)

    links = [
        {"url": reverse("common:explorer"), "name": "Explore data"},
        {"url": reverse("genes:index"), "name": "Genes"},
        {
            "url": reverse("genes:detail", args=[gene.id]),
            "name": "%s" % gene,
        },
        {
            "url": reverse("genes:similarities", args=[gene.id]),
            "name": "Phenotypic Similarities",
        },
    ]

    context = {
        "gene": gene,
        "similarities": similarities,
        "links": links,
        "active": "explorer",
    }
    return render(request, "genes/similarities_min.html", context)


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
    data = data.rename(columns={"dataset_id": "entry_id"})

    # Convert to scores dictionary for view
    scores = data[["entry_id", "valuez_x", "valuez_y", "name"]].to_dict(orient="index")

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
        "title1": gene1,
        "title2": gene2,
        "entry_type": "datasets",
        "scores": scores,
        "sim": sim.first(),
        "links": links,
        "active": "explorer",
    }
    return render(request, "genes/similar_scatterplot.html", context)





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
