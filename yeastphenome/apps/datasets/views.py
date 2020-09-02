from django.shortcuts import render
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.conf import settings
from django.core.paginator import Paginator
from django.views import generic

from yeastphenome.apps.common.utils import get_collections_by_year, get_dataset_genes
from yeastphenome.apps.papers.models import Paper
from yeastphenome.apps.datasets.models import Dataset, Data, Tag
from yeastphenome.apps.datasets.search import get_search_tags, run_search_tag_query
from yeastphenome.apps.conditions.models import ConditionType
from yeastphenome.apps.phenotypes.models import Observable


from libchebipy import ChebiEntity

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
        context.update(get_dataset_genes())
        return context


# Datasets Explorer (also the datasets index)


@ratelimit(key="ip", rate=rl_rate, block=rl_block)
def data_explorer(request):

    context = {
        "tags": get_search_tags(),
        "cart": request.session.get("cart", []),
        "DOWNLOAD_PREFIX": settings.DOWNLOAD_PREFIX,
    }
    if "q" in request.GET:
        query = request.GET["q"].strip()
        queryset = run_search_tag_query(query, return_instances=True)

        # 50 results per page
        paginator = Paginator(queryset, 50)
        page = request.GET.get("page")
        context["results"] = {
            "results": paginator.get_page(page),
            "count": queryset.count(),
        }

    else:
        # These are the original datasets that were associated with the growth class
        # This result is small enough to not be paginated
        context.update(
            {
                "datasets": Dataset.objects.filter(
                    conditionset__systematic_name="standard"
                )
                .filter(phenotype__observable__name__startswith="growth")
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
def download_all(request):

    datasets = (
        Dataset.objects.select_related("paper__latest_tested_status__status")
        .filter(paper__latest_data_status__status__name="loaded")
        .all()
    )

    datasets_list = list()
    for d in datasets:
        fields = [d.id, d.name, d.paper.pmid, d.paper.latest_tested_status]
        fields_str = "\t".join(["%s" % field for field in fields])
        datasets_list.append(fields_str)
    txt = "\n".join(datasets_list)

    txt = "id\tname\tpmid\tlatest_tested_status\n" + txt

    response = HttpResponse(txt, content_type="text/plain")
    response["Content-Disposition"] = (
        'attachment; filename="%s_datasets.txt"' % settings.DOWNLOAD_PREFIX
    )

    return response


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
