from django.db.models import Q
from django.shortcuts import render
from django.http import HttpResponse, StreamingHttpResponse
from django.shortcuts import get_object_or_404
from django.conf import settings
from django.core.paginator import Paginator
from django.views import generic
from django.contrib import messages

from django.views.decorators.cache import never_cache
from yeastphenome.apps.common.utils import get_collections_by_year, get_dataset_genes
from yeastphenome.apps.papers.models import Paper
from yeastphenome.apps.datasets.models import (
    Dataset,
    Data,
    Tag,
    Gene,
    GeneAlias,
    Collection,
)
from yeastphenome.apps.datasets.search import get_search_tags, run_search_tag_query
from yeastphenome.apps.datasets.utils import get_gene_metadata
from yeastphenome.apps.conditions.models import ConditionType
from yeastphenome.apps.phenotypes.models import Observable

from decimal import Decimal
from libchebipy import ChebiEntity
import csv

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
        context["collection_yearly_counts"] = get_collections_by_year(
            context["dataset"].collection
        )
        context.update(get_dataset_genes(context["dataset"].id))
        return context


# Explore by genes


@never_cache
@ratelimit(key="ip", rate=rl_rate, block=rl_block)
def gene_explorer(request):

    # prepare list of genes, plus genes and aliases
    context = {
        "genes": Gene.objects.values_list("systematic_name", flat=True).distinct(),
        "common_names": Gene.objects.values_list(
            "systematic_name", "common_name"
        ).distinct(),
        "aliases": GeneAlias.objects.values_list(
            "gene__systematic_name", "name"
        ).distinct(),
    }

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
            context["sims"] = {"top": sims[:10], "bottom": sims[len(sims) - 10 :]}

            # Filter to data with values defined, sorted greatest to smallest
            queryset = (
                Data.objects.exclude(Q(value=None) | Q(value=Decimal("NaN")))
                .filter(gene=context["gene"])
                .order_by("-value")
            )

            # We just will show top and bottom 10
            context["datasets_top"] = queryset[:10]
            context["datasets_bottom"] = queryset[len(queryset) - 10 :]

        except Gene.DoesNotExist:
            messages.warning(
                request,
                "Gene with systematic name %s does not exist in the database." % query,
            )
    return render(request, "genes/index.html", context)


# Datasets Explorer (also the datasets index)


@ratelimit(key="ip", rate=rl_rate, block=rl_block)
def data_explorer(request, collection_id=None):

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

    context = {
        "tags": get_search_tags(),
        "cart": request.session.get("cart", []),
        "DOWNLOAD_PREFIX": settings.DOWNLOAD_PREFIX,
    }
    if "q" in request.GET:
        query = request.GET["q"].strip()
        queryset = run_search_tag_query(
            query, return_instances=True, collection=collection
        )

        # 50 results per page
        paginator = Paginator(queryset, 50)
        page = request.GET.get("page")
        context["results"] = {
            "results": paginator.get_page(page),
            "count": queryset.count(),
        }

    else:

        if collection:
            datasets = Dataset.objects.filter(
                conditionset__systematic_name="standard", collection=collection
            )
        else:
            datasets = Dataset.objects.filter(conditionset__systematic_name="standard")

        # These are the original datasets that were associated with the growth class
        # This result is small enough to not be paginated
        context.update(
            {
                "datasets": datasets.filter(
                    phenotype__observable__name__startswith="growth"
                )
                .filter(control_conditionset__isnull=True)
                .filter(control_medium__isnull=True)
                .exclude(paper__latest_data_status__status__name="not relevant")
                .distinct(),
            }
        )

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
    """Download all dataset similarity scores (based on a gene)"""
    gene = Gene.objects.get(systematic_name=systematic_name)
    sims = gene.get_ranked_similar()

    # prepare response to write rows to
    response = HttpResponse(content_type="text/plain")
    filename = "%s_gene_similarities_%s.txt" % (
        settings.DOWNLOAD_PREFIX,
        systematic_name,
    )
    response["Content-Disposition"] = 'attachment; filename="%s"' % filename

    # prepare csv writer
    writer = csv.writer(response, delimiter="\t")
    columns = ["gene_similarity_id", "gene1", "gene2", "score", "pvalue"]
    writer.writerow(columns)

    for sim in sims:
        writer.writerow(
            [
                sim.id,
                sim.gene1.systematic_name,
                sim.gene2.systematic_name,
                float(sim.score),
                float(sim.pvalue),
            ]
        )
    return response


class Echo:
    """An object that implements just the write method of the file-like interface."""

    def write(self, value):
        """Write the value by returning it, instead of storing in a buffer."""
        return value


@ratelimit(key="ip", rate=rl_rate, block=rl_block)
def download_all(request, systematic_name=None):
    """Download all datasets. If a gene name is provided, filter to those"""
    if systematic_name:
        datasets = (
            Dataset.objects.select_related("paper__latest_tested_status__status")
            .filter(
                paper__latest_data_status__status__name="loaded",
                data__gene__systematic_name__iexact=systematic_name,
            )
            .distinct()
        )
    else:
        datasets = (
            Dataset.objects.select_related("paper__latest_tested_status__status")
            .filter(paper__latest_data_status__status__name="loaded")
            .distinct()
        )

    # prepare streaming response to write rows to
    pseudo_buffer = Echo()
    writer = csv.writer(pseudo_buffer, delimiter="\t")

    filename = (
        "%s_datasets_%s.txt" % (settings.DOWNLOAD_PREFIX, systematic_name)
        if systematic_name
        else "%s_datasets_%s.txt" % settings.DOWNLOAD_PREFIX
    )

    # The first row needs to be a column with headers
    writer.writerow(["id", "name", "pmid", "latest_tested_status"])
    response = StreamingHttpResponse(
        (
            writer.writerow([d.id, d.name, d.paper.pmid, d.paper.latest_tested_status])
            for d in datasets
        ),
        content_type="text/csv",
    )
    response["Content-Disposition"] = 'attachment; filename="%s"' % filename
    return response


@never_cache
@ratelimit(key="ip", rate=rl_rate, block=rl_block)
def download(request):

    file_header = ""

    # datasets = []
    # for key, value in request.GET.iteritems():
    #     datasets.append(key)
    datasets = sorted(request.GET)

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
                u"%s" % get_object_or_404(Dataset, pk=dataset_id)
                for dataset_id in datasets_ids
            ]
        )
        + "\n"
    )

    data_row = []
    for i, orf in enumerate(orfs):
        new_row = orf + "\t" + "\t".join([str(val) for val in matrix[i]])
        print(new_row)
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
        file_header = u"# Paper: %s (PMID %s)\n" % (paper, paper.pmid)

    if domain == "datasets":
        # datasets = get_object_or_404(Dataset, pk=id)
        datasets = Dataset.objects.filter(pk=id)
        dataset = datasets.first()
        file_header = u"# Paper: %s (PMID %s)\n# Dataset: %s\n" % (
            dataset.paper,
            dataset.paper.pmid,
            dataset,
        )

    if domain == "conditions":
        conditiontype = get_object_or_404(ConditionType, pk=id)
        datasets = conditiontype.datasets()
        file_header = u"# Condition: %s (ID %s)\n" % (conditiontype, conditiontype.id)

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
        file_header = u"# Data for conditions annotated as %s (ChEBI:%s)\n" % (
            chebi_entity.get_name(),
            id,
        )

    if domain == "phenotypes":
        phenotype = get_object_or_404(Observable, pk=id)
        datasets = phenotype.datasets()
        file_header = u"# Phenotype: %s (ID %s)\n" % (phenotype, phenotype.id)

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
                u"%s" % get_object_or_404(Dataset, pk=dataset_id)
                for dataset_id in datasets_ids
            ]
        )
        + "\n"
    )

    data_row = []
    for i, orf in enumerate(orfs):
        new_row = orf + "\t" + "\t".join([str(val) for val in matrix[i]])
        print(new_row)
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
