from django.db.models import Q
from django.shortcuts import render, redirect
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, reverse
from django.conf import settings

from django.views.decorators.cache import never_cache
from yeastphenome.apps.papers.models import Paper
from yeastphenome.apps.datasets.models import (
    DatasetSimilarity,
    Dataset,
    Data,
    Tag,
)
from yeastphenome.apps.genes.models import Gene, GeneAlias
from yeastphenome.apps.datasets.search import get_search_tags
from yeastphenome.apps.datasets.utils import send_file
from yeastphenome.apps.conditions.models import ConditionType, Medium
from yeastphenome.apps.phenotypes.models import Observable

from libchebipy import ChebiEntity
import os
import pandas
import tempfile

from ratelimit.decorators import ratelimit
from yeastphenome.settings import (
    VIEW_RATE_LIMIT as rl_rate,
    VIEW_RATE_LIMIT_BLOCK as rl_block,
)


@ratelimit(key="ip", rate=rl_rate, block=rl_block)
def dataset_detail(request, dataset_id):

    dataset = get_object_or_404(Dataset, pk=dataset_id)

    # Links should include the dataset detail page
    links = [
        {"url": reverse("common:explorer"), "name": "Explore data"},
        {"url": reverse("datasets:index"), "name": "Datasets"},
        {
            "url": reverse("datasets:dataset_detail", args=[dataset.id]),
            "name": dataset.name,
        },
    ]

    context = {"links": links, "active": "explorer", "dataset": dataset}

    # Get the top and bottom phenotypic scores
    context["datasets_top"] = dataset.get_data(reverse=False)[:10]
    context["datasets_bottom"] = dataset.get_data(reverse=True)[:10]

    # Get the top and bottom correlations
    context["sims_top"] = dataset.get_ranked_similar(reverse=False)[:10]
    context["sims_bottom"] = dataset.get_ranked_similar(reverse=True)[:10]

    return render(request, "datasets/detail.html", context)


@ratelimit(key="ip", rate=rl_rate, block=rl_block)
def similar_scatterplot(request, dataset1_id, dataset2_id):
    """Generate a scatterplot to compare two datasets based on phenotypic scores."""
    dataset1 = get_object_or_404(Dataset, pk=dataset1_id)
    dataset2 = get_object_or_404(Dataset, pk=dataset2_id)

    # Get the correlation to add
    sim = DatasetSimilarity.objects.filter(
        Q(dataset1=dataset1, dataset2=dataset2)
        | Q(dataset1=dataset2, dataset2=dataset1)
    )

    # Get gene values across datasets 1 and 2
    data1 = pandas.DataFrame(list(dataset1.data_set.values()))
    data2 = pandas.DataFrame(list(dataset2.data_set.values()))

    # Join the 2 dataframes using gene_id as the key
    data = data1.merge(data2, on="gene_id")

    # Only keep rows where both genes have values (are not null)
    data = data.loc[data["valuez_x"].notnull() & data["valuez_y"].notnull()]

    # Get gene names
    names = pandas.DataFrame(
        list(Gene.objects.filter(id__in=data["gene_id"].values).values())
    )

    # Add them to the data dataframe
    data = data.merge(
        names[["id", "systematic_name", "common_name"]],
        left_on="gene_id",
        right_on="id",
    )

    # Convert to scores dictionary for view
    scores = data[["gene_id", "valuez_x", "valuez_y", "systematic_name", "common_name"]]

    # This creates a warning that doesn't seem to be fixable
    scores["name"] = scores["common_name"] + "/" + scores["systematic_name"]
    scores = scores.rename(columns={"gene_id": "entry_id"})
    scores = scores.to_dict(orient="index")

    links = [
        {"url": reverse("common:explorer"), "name": "Explore data"},
        {"url": reverse("datasets:index"), "name": "Datasets"},
        {
            "url": reverse("datasets:dataset_detail", args=[dataset1.id]),
            "name": dataset1.short_name,
        },
        {
            "url": reverse("datasets:similar_dataset_table", args=[dataset1.id]),
            "name": "Similar Datasets",
        },
        {
            "url": reverse("datasets:dataset_detail", args=[dataset2.id]),
            "name": dataset2.short_name,
        },
    ]
    context = {
        "title1": dataset1.short_name,
        "title2": dataset2.short_name,
        "scores": scores,
        "entry_type": "genes",
        "sim": sim.first(),
        "links": links,
        "active": "explorer",
    }
    return render(request, "datasets/similar_scatterplot.html", context)


@never_cache
@ratelimit(key="ip", rate=rl_rate, block=rl_block)
def dataset_plot(request, dataset_id):
    """The dataset plot shows an interactive graph of the dataset, on which
    the user can click bars to see genes (and values) within a particular
    range
    """

    dataset = get_object_or_404(Dataset, pk=dataset_id)

    links = [
        {"url": reverse("common:explorer"), "name": "Explore data"},
        {"url": reverse("datasets:index"), "name": "Datasets"},
        {
            "url": reverse("datasets:dataset_detail", args=[dataset.id]),
            "name": dataset.name,
        },
        {
            "url": reverse("datasets:dataset_plot", args=[dataset.id]),
            "name": "Phenotypic Scores",
        },
    ]

    # prepare list of genes, plus genes and aliases
    context = get_dataset_gene_table_context(dataset)
    context.update({"dataset": dataset, "links": links, "active": "explorer"})
    return render(request, "datasets/plot.html", context)


def get_dataset_gene_table_context(dataset):
    """this context is needed for the graph."""
    context = {}
    genes = (
        dataset.data_set.exclude(valuez__isnull=True)
        .order_by("-valuez")
        .values_list("gene__systematic_name", "valuez", "gene__id", "gene__common_name")
        .distinct()
    )

    # Calculate ranking
    total_genes = genes.count()
    ranks = [(1 - (idx / total_genes)) * 100 for idx, _ in enumerate(genes)]

    gene_ids = [gene[2] for gene in genes]
    genes = [
        {
            "label": x[0],
            "gene_id": x[2],
            "value": float(x[1]),
            "name": x[3],
            "rank": round(ranks[i], 3),
        }
        for i, x in enumerate(genes)
        if x[3]
    ]
    context["aliases"] = (
        GeneAlias.objects.filter(gene__id__in=gene_ids)
        .values_list("gene__systematic_name", "name")
        .distinct()
    )
    context["common_names"] = (
        Gene.objects.filter(id__in=gene_ids)
        .exclude(common_name=None)
        .values_list("systematic_name", "common_name")
        .distinct()
    )
    context["dataset_genes"] = sorted(genes, key=lambda i: i["value"])
    context["active"] = "explorer"
    return context


@ratelimit(key="ip", rate=rl_rate, block=rl_block)
def similar_dataset_table(request, dataset_id):

    dataset = get_object_or_404(Dataset, pk=dataset_id)

    sims = (
        dataset.get_ranked_similar()
        .select_related("dataset2__name")
        .values_list("dataset2_id", "dataset2__name", "score", "pvalue")
    )

    links = [
        {"url": reverse("common:explorer"), "name": "Explore data"},
        {"url": reverse("datasets:index"), "name": "Datasets"},
        {
            "url": reverse("datasets:dataset_detail", args=[dataset.id]),
            "name": dataset.name,
        },
        {
            "url": reverse("datasets:similar_dataset_table", args=[dataset.id]),
            "name": "Similar Datasets",
        },
    ]
    total = sims.count()
    ranks = [(1 - (idx / total)) * 100 for idx, sim in enumerate(sims)]
    context = {
        "dataset": dataset,
        "datasets": sims,
        "ranks": ranks,
        "links": links,
        "active": "explorer",
    }
    return render(request, "datasets/dataset_similarity_explorer.html", context)


# Datasets Explorer (also the datasets index)
@never_cache
@ratelimit(key="ip", rate=rl_rate, block=rl_block)
def data_explorer_redirect(request, query):
    return redirect("%s?query=%s" % (reverse("datasets:index"), query))


@never_cache
@ratelimit(key="ip", rate=rl_rate, block=rl_block)
def data_explorer(request, collection_id=None):
    """Dataset search is equivalent to the API version, but instead takes GET
    parameters to derive tags and a query. This will enable users to copy
    a particular search and share it with colleagues.
    """
    # Table will be rendered server side, and we pass query parameters
    taglist = []
    for tag in request.GET.get("query", "").split("|"):
        if not tag:
            continue
        taglist.append({"value": tag, "code": "query"})

    links = [
        {"url": reverse("common:explorer"), "name": "Explore data"},
        {"url": reverse("datasets:index"), "name": "Datasets"},
    ]
    context = {
        "taglist": taglist,
        "collection_id": collection_id,
        "links": links,
        "active": "explorer",
        "tags": get_search_tags(),
        "cart": request.session.get("cart", []),
        "DOWNLOAD_PREFIX": settings.DOWNLOAD_PREFIX,
    }
    return render(request, "datasets/explorer.html", context)


@ratelimit(key="ip", rate=rl_rate, block=rl_block)
def tag(request, id):

    t = get_object_or_404(Tag, pk=id)

    datasets = (
        Dataset.objects.all_valid().filter(tags=id)
    )

    links = [
        {"url": reverse("common:explorer"), "name": "Explore data"},
        {"url": reverse("datasets:index"), "name": "Datasets"},
        {
            "url": "%s?query=%s" % (reverse("datasets:index"), t.name),
            "name": "Tag %s" % t.name,
        },
    ]

    return render(
        request,
        "datasets/tag.html",
        {
            "links": links,
            "active": "explorer",
            "tag": t,
            "datasets": datasets,
            "DOWNLOAD_PREFIX": settings.DOWNLOAD_PREFIX,
            "USER_AUTH": request.user.is_authenticated,
        },
    )


@ratelimit(key="ip", rate=rl_rate, block=rl_block)
def download_dataset_similarities(request, dataset_id):
    """Download all DatasetSimilarity values for a given dataset"""

    import pandas as pd

    dataset = get_object_or_404(Dataset, pk=dataset_id)

    sims = (
        dataset.get_ranked_similar()
        .select_related("dataset1__name", "dataset2__name")
        .values_list("dataset1__name", "dataset2__name", "score", "pvalue")
    )

    df = pd.DataFrame(sims)
    df.columns = ["Dataset1", "Dataset2", "Correlation", "P-value"]

    filename = "%s_dataset%d_similarities.txt" % (
        settings.DOWNLOAD_PREFIX,
        dataset.id,
    )

    # Prepare the HttpResponse
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = "attachment; filename=%s" % filename

    # Print data matrix to response buffer
    df.to_csv(path_or_buf=response, sep="\t", index=False)

    return response


@ratelimit(key="ip", rate=rl_rate, block=rl_block)
def download_observable_datasets_list(request, observable_id):
    """Download all datasets associated with an observable"""
    import pandas

    observable = get_object_or_404(Observable, pk=observable_id)

    filename = "%s_observable_datasets_list_%s.txt" % (
        settings.DOWNLOAD_PREFIX,
        observable_id,
    )

    datasets = (
        observable.datasets()
        .select_related("paper__latest_tested_status__status")
        .filter(paper__latest_data_status__status__name="loaded")
        .values_list("id", "name", "paper__pmid", "paper__latest_tested_status")
        .distinct()
    )
    df = pandas.DataFrame(datasets)
    df.columns = ["id", "name", "pmid", "latest_tested_status"]
    exported_file = os.path.join(tempfile.gettempdir(), filename)
    if not os.path.exists(exported_file):
        df.to_csv(exported_file, sep="\t", index=None)
    return send_file(exported_file)


@ratelimit(key="ip", rate=rl_rate, block=rl_block)
def download_dataset_cart(request):
    """download all the dataset objects in the user's cart"""
    # Get dataset ids from cart
    datasets = request.session.get("cart", [])
    response = download_dataset_scores(request, datasets)

    # Clear the cart on download
    if "cart" in request.session:
        del request.session["cart"]

    return response


@ratelimit(key="ip", rate=rl_rate, block=rl_block)
def download_dataset_scores(request, datasets=None, filename=None):
    """Downloads scores for one dataset or a list of datasets. Produces a gene x dataset matrix."""

    import pandas as pd
    import numpy as np

    # Dataset ids can be optionally provided
    datasets = datasets or []

    if not datasets:
        for key, value in request.GET.items():
            try:
                datasets.append(int(key))
            except:
                pass

    # Get all data as a list of dicts
    data = list(
        Data.objects.filter(dataset_id__in=datasets)
        .filter(dataset__data_source__release=True)
        .values()
    )

    # Transform data into a DataFrame (long form)
    data_df = pd.DataFrame(data)

    # Prepare the HttpResponse
    filename = filename or "%s_data.txt" % settings.DOWNLOAD_PREFIX
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="%s"' % filename

    # https://github.com/johnculviner/jquery.fileDownload/blob/master/src/Scripts/jquery.fileDownload.js#L11
    # If this is not set, callbacks do not work
    response["Set-Cookie"] = "fileDownload=true; path=/"

    # If there are no datasets, cut out early and return empty file
    if data_df.empty:
        data_df.to_csv(path_or_buf=response, sep="\t", na_rep="NaN")
        return response

    # Make sure that values are numeric
    data_df["valuez"] = data_df["valuez"].astype(float)

    # Pivot DataFrame from long to wide form
    data_matrix = pd.pivot_table(
        data_df,
        index="gene_id",
        columns="dataset_id",
        values="valuez",
        fill_value=np.nan,
    )

    # Replace gene_ids with ORF names
    genes = list(Gene.objects.filter(id__in=data_matrix.index.values).values())
    genes_df = pd.DataFrame(genes)
    genes_df.set_index("id", inplace=True)
    data_matrix.index = genes_df.reindex(index=data_matrix.index.values)[
        "systematic_name"
    ].values
    data_matrix.index.rename("ORF", inplace=True)

    # Replace dataset_ids with dataset names
    datasets = list(Dataset.objects.filter(id__in=data_matrix.columns.values).values())
    datasets_df = pd.DataFrame(datasets)
    datasets_df.set_index("id", inplace=True)
    data_matrix.columns = datasets_df.reindex(index=data_matrix.columns.values)[
        "name"
    ].values

    # Print data matrix to response buffer
    data_matrix.to_csv(path_or_buf=response, sep="\t", na_rep="NaN")

    return response


@ratelimit(key="ip", rate=rl_rate, block=rl_block)
def download_observable_datasets(request, observable_id):
    """Download all datasets associated with an observable"""

    observable = get_object_or_404(Observable, pk=observable_id)
    filename = "%s_observable_datasets_%s.txt" % (
        settings.DOWNLOAD_PREFIX,
        observable_id,
    )
    return download_dataset_scores(
        request, datasets=observable.datasets(), filename=filename
    )


@ratelimit(key="ip", rate=rl_rate, block=rl_block)
def download_paper_datasets(request, paper_id):
    """Download all datasets associated with a paper"""

    paper = get_object_or_404(Paper, pk=paper_id)
    filename = "%s_paper_data_%s.txt" % (settings.DOWNLOAD_PREFIX, paper.id)
    return download_dataset_scores(
        request, datasets=paper.dataset_set.all(), filename=filename
    )


@ratelimit(key="ip", rate=rl_rate, block=rl_block)
def download_condition_datasets(request, condition_id):
    """Download all datasets associated with a condition type"""

    condition = get_object_or_404(ConditionType, pk=condition_id)
    filename = "%s_condition_data_%s.txt" % (settings.DOWNLOAD_PREFIX, condition.id)
    return download_dataset_scores(
        request, datasets=condition.datasets(), filename=filename
    )


@ratelimit(key="ip", rate=rl_rate, block=rl_block)
def download_medium_datasets(request, medium_id):
    """Download all datasets associated with a medium"""

    medium = get_object_or_404(Medium, pk=medium_id)

    filename = "%s_medium_datasets_%s.txt" % (
        settings.DOWNLOAD_PREFIX,
        medium.display_name,
    )
    return download_dataset_scores(
        request, datasets=medium.datasets(), filename=filename
    )


@ratelimit(key="ip", rate=rl_rate, block=rl_block)
def data(request, domain, id):

    file_header = ""

    if domain == "papers":
        paper = get_object_or_404(Paper, pk=id)
        datasets = paper.dataset_set
        file_header = "# Paper: %s (PMID %s)\n" % (paper, paper.pmid)

    if domain == "datasets":
        # datasets = get_object_or_404(Dataset, pk=id)
        datasets = Dataset.objects.filter(pk=id)
        dataset = datasets.first()
        file_header = "# Paper: %s (PMID %s)\n# Dataset: %s\n" % (
            dataset.paper,
            dataset.paper.pmid,
            dataset,
        )

    if domain == "conditions":
        conditiontype = get_object_or_404(ConditionType, pk=id)
        datasets = conditiontype.datasets()
        file_header = "# Condition: %s (ID %s)\n" % (conditiontype, conditiontype.id)

    if domain == "chebi":
        chebi_entity = ChebiEntity("CHEBI:" + str(id))
        children = []
        for relation in chebi_entity.get_incomings():
            if relation.get_type() == "has_role":
                tid = relation.get_target_chebi_id()
                tid = int(filter(str.isdigit, tid))
                children.append(tid)
        datasets = Dataset.objects.filter(
            conditionset__conditions__type__chebi_id__in=children
        )
        file_header = "# Data for conditions annotated as %s (ChEBI:%s)\n" % (
            chebi_entity.get_name(),
            id,
        )

    if domain == "phenotypes":
        phenotype = get_object_or_404(Observable, pk=id)
        datasets = phenotype.datasets()
        file_header = "# Phenotype: %s (ID %s)\n" % (phenotype, phenotype.id)

    data = Data.objects.filter(dataset_id__in=datasets.values("id")).all()

    orfs = list(data.values_list("orf", flat=True).distinct())
    datasets_ids = list(
        data.values_list("dataset_id", flat=True).order_by("dataset__paper").distinct()
    )
    matrix = [[None] * len(datasets_ids) for i in orfs]

    for datapoint in data:
        i = orfs.index(datapoint.orf)
        j = datasets_ids.index(datapoint.dataset_id)
        matrix[i][j] = datapoint.value

    column_headers = (
        "\t"
        + "\t".join(
            [
                "%s" % get_object_or_404(Dataset, pk=dataset_id)
                for dataset_id in datasets_ids
            ]
        )
        + "\n"
    )

    data_row = []
    for i, orf in enumerate(orfs):
        new_row = orf + "\t" + "\t".join([str(val) for val in matrix[i]])
        data_row.append(new_row)

    txt3 = "\n".join(data_row)

    response = HttpResponse(
        file_header + column_headers + txt3, content_type="text/plain"
    )
    response["Content-Disposition"] = 'attachment; filename="%s_%s_%s_data.txt"' % (
        settings.DOWNLOAD_PREFIX,
        domain,
        id,
    )

    return response
