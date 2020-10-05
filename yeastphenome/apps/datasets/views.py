from django.db.models import Q
from django.shortcuts import render
from django.http import HttpResponse, Http404
from django.shortcuts import get_object_or_404
from django.conf import settings
from django.core.paginator import Paginator
from django.contrib import messages
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
    GeneSimilarity,
    Collection,
)
from yeastphenome.apps.datasets.search import get_search_tags, run_search_tag_query
from yeastphenome.apps.datasets.utils import get_gene_metadata, send_file
from yeastphenome.apps.conditions.models import ConditionType
from yeastphenome.apps.phenotypes.models import Observable

from decimal import Decimal
from libchebipy import ChebiEntity
import os
import tempfile
import pandas

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
        bottom = sims[len(sims) - 10 :]
        bottom.reverse()
        context["sims"] = {"top": sims[:10], "bottom": bottom}

        # Filter to data with values defined, sorted greatest to smallest
        queryset = (
            Data.objects.filter(dataset=context["dataset"])
            .exclude(Q(value=None) | Q(value=Decimal("NaN")))
            .order_by("-value")
            .values_list("gene__systematic_name", "gene__common_name", "value")
        )

        context["datasets_top"] = queryset[:10]
        context["datasets_bottom"] = queryset[len(queryset) - 10 :]
        context["datasets_bottom"].reverse()
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

    # prepare list of genes, plus genes and aliases
    context = get_dataset_gene_table_context(dataset)
    context.update({"dataset": dataset})
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
    ranks = [(idx / total_genes) * 100 for idx, _ in enumerate(genes)]

    gene_ids = [gene[2] for gene in genes]
    genes = [
        {"label": x[0], "value": float(x[1]), "name": x[3], "rank": round(ranks[i], 3)}
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
    return context


@ratelimit(key="ip", rate=rl_rate, block=rl_block)
def gene_explorer(request):

    # prepare list of genes, plus genes and aliases
    context = get_gene_names_context()

    # A get request for a gene should display it to start
    if "q" in request.GET:
        query = request.GET["q"].strip()

        try:
            # First look up based on systematic or common name
            gene = Gene.objects.get(
                Q(systematic_name__iexact=query) | Q(common_name__iexact=query)
            )

            # If not found, try for an alias
            if not gene:
                gene = GeneAlias.objects.get(name__iexact=query).gene_set.first()
            context["gene"] = gene
            context["metadata"] = get_gene_metadata(context["gene"].systematic_name)

            # Get top/bottom 10 most similar
            sims = list(context["gene"].get_ranked_similar())
            bottom = sims[len(sims) - 10 :]
            bottom.reverse()

            context["sims"] = {"top": sims[:10], "bottom": bottom}

            # Filter to data with values defined, sorted greatest to smallest
            queryset = (
                Data.objects.exclude(Q(value=None) | Q(value=Decimal("NaN")))
                .filter(gene=context["gene"])
                .order_by("-value")
            )

            # We just will show top and bottom 10
            context["datasets_top"] = queryset[:10]
            context["datasets_bottom"] = queryset[len(queryset) - 10 :]
            context["datasets_bottom"].reverse()

        except Gene.DoesNotExist:
            messages.warning(
                request,
                "Gene with systematic name %s does not exist in the database." % query,
            )
    return render(request, "genes/index.html", context)


@ratelimit(key="ip", rate=rl_rate, block=rl_block)
def similar_genes(request, systematic_name):

    try:
        gene = Gene.objects.get(
            Q(systematic_name__iexact=systematic_name)
            | Q(common_name__iexact=systematic_name)
        )
    except Gene.DoesNotExist:
        raise Http404

    sims = (
        GeneSimilarity.objects.filter(gene1=gene)
        .values_list("gene2__systematic_name", "gene2__common_name", "score", "pvalue")
        .order_by("-score")
        .distinct()
    )
    total_sims = sims.count()
    ranks = [(idx / total_sims) * 100 for idx, sim in enumerate(sims)]
    context = get_gene_names_context()
    context.update({"gene": gene, "sims": sims, "ranks": ranks})
    return render(request, "genes/similar_genes.html", context)


@never_cache
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

    total = sims.count()
    ranks = [(idx / total) * 100 for idx, sim in enumerate(sims)]
    context = {"dataset": dataset, "datasets": sims, "ranks": ranks}
    return render(request, "datasets/dataset_similarity_explorer.html", context)


@ratelimit(key="ip", rate=rl_rate, block=rl_block)
def gene_datasets(request, systematic_name):

    try:
        gene = Gene.objects.get(
            Q(systematic_name__iexact=systematic_name)
            | Q(common_name__iexact=systematic_name)
        )
    except Gene.DoesNotExist:
        raise Http404

    queryset = (
        Data.objects.filter(gene=gene)
        .exclude(Q(value=None) | Q(value=Decimal("NaN")))
        .order_by("-value")
    )
    total = queryset.count()
    ranks = [(idx / total) * 100 for idx, sim in enumerate(queryset)]
    context = get_gene_names_context()
    context.update({"gene": gene, "datasets": queryset, "ranks": ranks})
    return render(request, "genes/gene_datasets.html", context)


# Datasets Explorer (also the datasets index)


@never_cache
@ratelimit(key="ip", rate=rl_rate, block=rl_block)
def data_explorer(request, collection_id=None):
    """Dataset search is equivalent to the API version, but instead takes GET
    parameters to derive tags and a query. This will enable users to copy
    a particular search and share it with colleagues.
    """
    # The user can optionally be searching by a collection
    collection = None
    if collection_id:
        try:
            collection = Collection.objects.get(id=collection_id)
            messages.info(
                request,
                "Datasets shown are for collection %s (%s)"
                % (collection.name, collection.shortname),
            )
        except Collection.DoesNotExist:
            messages.warning(
                request, "We could not find collection with id %s" % collection_id
            )

    taglist = []
    for key in [
        "datatype",
        "tag",
        "medium",
        "conditions",
        "collection",
        "phenotype",
        "query",
    ]:
        for tag in request.GET.get(key, "").split(","):
            if not tag:
                continue
            taglist.append({"value": tag, "code": key})

    context = {
        "tags": get_search_tags(),
        "cart": request.session.get("cart", []),
        "DOWNLOAD_PREFIX": settings.DOWNLOAD_PREFIX,
    }

    # Use same function above to update search results
    queryset = []
    if taglist:
        queryset = run_search_tag_query(
            query=None, taglist=taglist, return_instances=True, collection=collection
        )

        # 50 results per page
        paginator = Paginator(queryset, 50)
        page = request.GET.get("page")
        context["results"] = {
            "results": paginator.get_page(page),
            "count": queryset.count(),
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

    return render(
        request,
        "datasets/tag.html",
        {
            "tag": t,
            "datasets": datasets,
            "DOWNLOAD_PREFIX": settings.DOWNLOAD_PREFIX,
            "USER_AUTH": request.user.is_authenticated,
        },
    )


@ratelimit(key="ip", rate=rl_rate, block=rl_block)
def download_sims(request, systematic_name):
    """Download all GeneSimilary values (based on a gene)"""
    try:
        gene = Gene.objects.get(systematic_name=systematic_name)
    except Gene.DoesNotExist:
        raise Http404

    sims = gene.get_ranked_similar().values_list(
        "id", "gene1", "gene2", "score", "pvalue"
    )

    filename = "%s_gene_similarities_%s.txt" % (
        settings.DOWNLOAD_PREFIX,
        systematic_name,
    )

    df = pandas.DataFrame(sims)
    df.columns = ["gene_similarity_id", "gene1", "gene2", "score", "pvalue"]
    exported_file = os.path.join(tempfile.gettempdir(), filename)
    if not os.path.exists(exported_file):
        df.to_csv(exported_file, sep=",", index=None)
    return send_file(exported_file)


@ratelimit(key="ip", rate=rl_rate, block=rl_block)
def download_dataset_sims(request, dataset_id):
    """Download all DatasetSimilarity scores (based on a dataset)"""
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
        df.to_csv(exported_file, sep=",", index=None)
    return send_file(exported_file)


@ratelimit(key="ip", rate=rl_rate, block=rl_block)
def download_all(request, systematic_name=None):
    """Download all datasets. If a gene name is provided, filter to those"""

    if systematic_name in ["all", None]:
        datasets = (
            Dataset.objects.select_related("paper__latest_tested_status__status")
            .filter(paper__latest_data_status__status__name="loaded")
            .values_list("id", "name", "paper__pmid", "paper__latest_tested_status")
            .distinct()
        )

    else:
        datasets = (
            Dataset.objects.filter(data__gene__systematic_name=systematic_name)
            .select_related("paper__latest_tested_status__status")
            .filter(
                paper__latest_data_status__status__name="loaded",
            )
            .values_list("id", "name", "paper__pmid", "paper__latest_tested_status")
            .distinct()
        )

    filename = (
        "%s_datasets_%s.txt" % (settings.DOWNLOAD_PREFIX, systematic_name)
        if systematic_name
        else "%s_datasets_%s.txt" % settings.DOWNLOAD_PREFIX
    )

    df = pandas.DataFrame(datasets)
    df.columns = ["id", "name", "pmid", "latest_tested_status"]
    exported_file = os.path.join(tempfile.gettempdir(), filename)
    if not os.path.exists(exported_file):
        df.to_csv(exported_file, sep=",", index=None)
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
