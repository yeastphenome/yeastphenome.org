from django.db.models import Q
from django.shortcuts import render, redirect
from django.http import HttpResponse, Http404
from django.shortcuts import get_object_or_404, reverse
from django.conf import settings
from django.views import generic

from django.views.decorators.cache import never_cache
from yeastphenome.apps.papers.models import Paper
from yeastphenome.apps.datasets.models import (
    Dataset,
    DatasetSimilarity,
    Data,
    Tag,
    Gene,
    GeneAlias,
)
from yeastphenome.apps.datasets.search import (
    get_search_tags,
    get_gene_search_tags,
)
from yeastphenome.apps.datasets.utils import (
    send_file,
    prepare_dataset_download,
)
from yeastphenome.apps.conditions.models import ConditionType, Medium
from yeastphenome.apps.phenotypes.models import Observable

from decimal import Decimal
from libchebipy import ChebiEntity
import os
import tempfile

from ratelimit.mixins import RatelimitMixin
from ratelimit.decorators import ratelimit
from yeastphenome.settings import (
    VIEW_RATE_LIMIT as rl_rate,
    VIEW_RATE_LIMIT_BLOCK as rl_block,
)


class DatasetDetailView(generic.DetailView, RatelimitMixin):
    model = Dataset
    template_name = "datasets/detail.html"
    context_object_name = "dataset"
    ratelimit_key = "ip"
    ratelimit_rate = rl_rate
    ratelimit_block = rl_block

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Get DatasetSimilarity values
        sims = (
            DatasetSimilarity.objects.filter(dataset1=context["dataset"])
            .values_list("dataset2_id", "dataset2__name", "score", "pvalue")
            .order_by("-score")
            .distinct()
        )
        # Show bottom values ascending, top values descending
        top = []
        bottom = []
        if sims.count() >= 10:
            top = sims[:10]
            bottom = sims[len(sims) - 10 :]
            bottom.reverse()
        context["sims"] = {"top": top, "bottom": bottom}

        # Filter to data with values defined, sorted greatest to smallest
        queryset = (
            Data.objects.filter(dataset=context["dataset"])
            .exclude(Q(value=None) | Q(value=Decimal("NaN")))
            .order_by("-value")
            .values_list("gene__systematic_name", "gene__common_name", "value")
        )

        # Links should include the dataset detail page
        links = [
            {"url": reverse("common:explorer"), "name": "Explore data"},
            {"url": reverse("datasets:index"), "name": "Datasets"},
            {
                "url": reverse("datasets:detail", args=[context["dataset"].id]),
                "name": context["dataset"].name,
            },
        ]

        datasets_top = queryset[:10]
        datasets_bottom = []
        if queryset.count() >= 10:
            datasets_bottom = queryset[len(queryset) - 10 :]
            datasets_bottom.reverse()
        context["datasets_top"] = datasets_top
        context["datasets_bottom"] = datasets_bottom
        context["links"] = links
        context["active"] = "explorer"
        return context


@never_cache
@ratelimit(key="ip", rate=rl_rate, block=rl_block)
def dataset_plot(request, dataset_id):
    """The dataset plot shows an interactive graph of the dataset, on which
    the user can click bars to see genes (and values) within a particular
    range
    """
    try:
        dataset = Dataset.objects.get(id=dataset_id)
    except Dataset.DoesNotExist:
        raise Http404

    links = [
        {"url": reverse("common:explorer"), "name": "Explore data"},
        {"url": reverse("datasets:index"), "name": "Datasets"},
        {
            "url": reverse("datasets:detail", args=[dataset.id]),
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


# Explore by genes


def get_gene_names_context():
    """This context is needed for the gene search box, to find based on gene
    systematic, common name, or alias.
    """
    return {
        "genes": Gene.objects.values_list("systematic_name", flat=True).distinct(),
        "common_names": Gene.objects.values_list(
            "systematic_name", "common_name"
        ).distinct(),
        "aliases": GeneAlias.objects.values_list(
            "gene__systematic_name", "name"
        ).distinct(),
    }


def get_dataset_gene_table_context(dataset):
    """this context is needed for the graph."""
    context = {}
    genes = (
        dataset.data_set.exclude(Q(value=None) | Q(value=Decimal("NaN")))
        .order_by("-value")
        .values_list("gene__systematic_name", "value", "gene__id", "gene__common_name")
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
def gene_explorer(request):

    taglist = []
    for key in [
        "query",
    ]:
        for tag in request.GET.get(key, "").split("|"):
            if not tag:
                continue
            taglist.append(tag)

    print(taglist)
    links = [
        {"url": reverse("common:explorer"), "name": "Explore data"},
        {"url": reverse("genes:index"), "name": "Genes"},
    ]
    context = {
        "links": links,
        "active": "explorer",
        "tags": get_gene_search_tags(),
        "taglist": taglist,
    }
    return render(request, "genes/index.html", context)


@ratelimit(key="ip", rate=rl_rate, block=rl_block)
def gene_detail(request, gene_id):

    try:
        gene = Gene.objects.get(pk=gene_id)
    except Gene.DoesNotExist:
        raise Http404

    # Assemble links assuming on root of page
    links = [
        {"url": reverse("common:explorer"), "name": "Explore data"},
        {"url": reverse("genes:index"), "name": "Genes"},
        {
            "url": reverse("genes:detail", args=[gene.id]),
            "name": "%s" % gene,
        },
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

    try:
        gene = Gene.objects.get(pk=gene_id)
    except Gene.DoesNotExist:
        raise Http404

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
def similar_dataset_table(request, dataset_id):

    try:
        dataset = Dataset.objects.get(id=dataset_id)
    except Dataset.DoesNotExist:
        raise Http404

    sims = (
        DatasetSimilarity.objects.filter(dataset1=dataset)
        .values_list("dataset2_id", "dataset2__name", "score", "pvalue")
        .order_by("-score")
        .distinct()
    )

    links = [
        {"url": reverse("common:explorer"), "name": "Explore data"},
        {"url": reverse("datasets:index"), "name": "Datasets"},
        {
            "url": reverse("datasets:detail", args=[dataset.id]),
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


@ratelimit(key="ip", rate=rl_rate, block=rl_block)
def gene_datasets(request, gene_id):
    import numpy as np

    try:
        gene = Gene.objects.get(pk=gene_id)
    except Gene.DoesNotExist:
        raise Http404

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
    datapoints = (
        Data.objects.filter(gene=gene)
        .exclude(valuez__isnull=True)
        .order_by("-valuez")
        .values_list("valuez")
    )

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
    for key in [
        "datatype",
        "tags",
        "medium",
        "conditions",
        "collection",
        "phenotype",
        "query",
    ]:
        for tag in request.GET.get(key, "").split("|"):
            if not tag:
                continue
            taglist.append({"value": tag, "code": key})

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
        Dataset.objects.filter(tags=id)
        .exclude(paper__latest_data_status__status__name="not relevant")
        .distinct()
    )

    links = [
        {"url": reverse("common:explorer"), "name": "Explore data"},
        {"url": reverse("datasets:index"), "name": "Datasets"},
        {
            "url": "%s?tags=%s" % (reverse("datasets:index"), t.name),
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
def download_sims(request, gene_id):
    """Download all GeneSimilary values (based on a gene)"""
    import pandas

    try:
        gene = Gene.objects.get(id=gene_id)
    except Gene.DoesNotExist:
        raise Http404

    sims = gene.get_ranked_similar().values_list(
        "id", "gene1", "gene2", "score", "pvalue"
    )

    filename = "%s_gene_similarities_%s.txt" % (
        settings.DOWNLOAD_PREFIX,
        gene.systematic_name,
    )

    df = pandas.DataFrame(sims)
    df.columns = ["gene_similarity_id", "gene1", "gene2", "score", "pvalue"]
    exported_file = os.path.join(tempfile.gettempdir(), filename)
    if not os.path.exists(exported_file):
        df.to_csv(exported_file, sep="\t", index=None)
    return send_file(exported_file)


@ratelimit(key="ip", rate=rl_rate, block=rl_block)
def download_dataset_sims(request, dataset_id):
    """Download all DatasetSimilarity scores (based on a dataset)"""
    import pandas

    try:
        dataset = Dataset.objects.get(id=dataset_id)
    except Dataset.DoesNotExist:
        raise Http404

    sims = (
        DatasetSimilarity.objects.filter(Q(dataset1=dataset) | Q(dataset2=dataset))
        .values_list("id", "dataset1_id", "dataset2_id", "score", "pvalue")
        .order_by("-score")
        .distinct()
    )

    filename = "%s_dataset_%s_similarities.txt" % (
        settings.DOWNLOAD_PREFIX,
        dataset.id,
    )

    df = pandas.DataFrame(sims)
    df.columns = ["dataset_similarity_id", "dataset1", "dataset2", "score", "pvalue"]
    exported_file = os.path.join(tempfile.gettempdir(), filename)
    if not os.path.exists(exported_file):
        df.to_csv(exported_file, sep="\t", index=None)
    return send_file(exported_file)


@ratelimit(key="ip", rate=rl_rate, block=rl_block)
def download_observable_datasets_list(request, observable_id):
    """Download all datasets associated with an observable"""
    import pandas

    try:
        observable = Observable.objects.get(id=observable_id)
    except Observable.DoesNotExist:
        raise Http404

    filename = "%s_observable_datasets_list_%s.txt" % (
        settings.DOWNLOAD_PREFIX,
        observable.name,
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
def download_all(request, gene_id=None):
    """Download all datasets. If a gene name is provided, filter to those"""
    import pandas

    if gene_id in ["all", None]:
        datasets = (
            Dataset.objects.select_related("paper__latest_tested_status__status")
            .filter(paper__latest_data_status__status__name="loaded")
            .filter(data_source__release=True)
            .values_list("id", "name", "paper__pmid", "paper__latest_tested_status")
            .distinct()
        )

    else:
        datasets = (
            Dataset.objects.filter(data__gene__id=gene_id)
            .select_related("paper__latest_tested_status__status")
            .filter(
                paper__latest_data_status__status__name="loaded",
            )
            .values_list("id", "name", "paper__pmid", "paper__latest_tested_status")
            .distinct()
        )

    filename = (
        "%s_datasets_%s.txt" % (settings.DOWNLOAD_PREFIX, gene_id)
        if gene_id
        else "%s_datasets.txt" % settings.DOWNLOAD_PREFIX
    )

    df = pandas.DataFrame(datasets)
    df.columns = ["id", "name", "pmid", "latest_tested_status"]
    exported_file = os.path.join(tempfile.gettempdir(), filename)
    if not os.path.exists(exported_file):
        df.to_csv(exported_file, sep="\t", index=None)
    return send_file(exported_file)


@ratelimit(key="ip", rate=rl_rate, block=rl_block)
def download(request):
    file_header = ""

    # View passes: ?papersTable_length=10&14=on&26=on
    datasets = []
    for key, value in request.GET.items():
        try:
            datasets.append(int(key))
        except:
            pass

    data = (
        Data.objects.filter(dataset_id__in=datasets)
        .filter(dataset__data_source__release=True)
        .all()
    )

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
        "ORF\t"
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
    response["Content-Disposition"] = 'attachment; filename="%s_data.txt"' % (
        settings.DOWNLOAD_PREFIX
    )

    return response


@ratelimit(key="ip", rate=rl_rate, block=rl_block)
def download_observable_datasets(request, observable_id):
    """Download all datasets associated with an observable"""

    try:
        observable = Observable.objects.get(id=observable_id)
    except Observable.DoesNotExist:
        raise Http404

    filename = "%s_observable_datasets_%s.txt" % (
        settings.DOWNLOAD_PREFIX,
        observable.name,
    )

    # Returns a pandas dataframe to download from list of dataset ids
    df = prepare_dataset_download(
        observable.datasets().filter(data_source__release=True)
    )
    exported_file = os.path.join(tempfile.gettempdir(), filename)
    if not os.path.exists(exported_file):
        df.to_csv(exported_file, sep="\t", index=None)
    return send_file(exported_file)


@ratelimit(key="ip", rate=rl_rate, block=rl_block)
def download_medium_datasets(request, medium_id):
    """Download all datasets associated with a medium"""

    try:
        medium = Medium.objects.get(id=medium_id)
    except Medium.DoesNotExist:
        raise Http404

    filename = "%s_medium_datasets_%s.txt" % (
        settings.DOWNLOAD_PREFIX,
        medium.display_name,
    )

    # Returns a pandas dataframe to download from list of dataset ids
    df = prepare_dataset_download(medium.datasets().filter(data_source__release=True))
    exported_file = os.path.join(tempfile.gettempdir(), filename)
    if not os.path.exists(exported_file):
        df.to_csv(exported_file, sep="\t", index=None)
    return send_file(exported_file)


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
