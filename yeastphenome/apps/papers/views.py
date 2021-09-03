from django.shortcuts import render
from django.db.models import F
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.conf import settings

from yeastphenome.apps.papers.models import Paper
from yeastphenome.apps.papers.utils import (
    get_pubmed_paper_context,
    get_pubmed_paper,
    get_paper_references_context,
)
from yeastphenome.settings import (
    VIEW_RATE_LIMIT as rl_rate,
    VIEW_RATE_LIMIT_BLOCK as rl_block,
)

from ratelimit.decorators import ratelimit


@ratelimit(key="ip", rate=rl_rate, block=rl_block)
def detail(request, paper_id):
    p = get_object_or_404(Paper, pk=paper_id)

    datasets = p.datasets.all_valid()
    num_datasets = datasets.count()

    datasets = datasets[:10].values(
        dataset_id=F("id"),
        dataset_paper_name=F("paper__systematic_name"),
        dataset_phenotype_name=F("phenotype__name"),
        dataset_conditionset_name=F("conditionset__display_name"),
        dataset_medium_name=F("medium__display_name"),
        dataset_collection_name=F("collection__shortname"),
        dataset_data_name=F("data_available__name"),
    )

    context = {"paper": p, "datasets": datasets, "num_datasets": num_datasets}

    # Give credit if credit is due.
    names = p.acknowledgements_list_as_str()
    to_acknowledge = []
    if p.acknowledge_data():
        to_acknowledge.append("the data")
    if p.acknowledge_tested():
        to_acknowledge.append("the list of tested strains")
    if names:
        thanks = (
            " and ".join(to_acknowledge)
            + " for this paper were kindly provided by "
            + names
            + "."
        )
        context["thanks"] = thanks

    # Fetch article info from Pubmed, share data from one call
    if p.pmid != 0:
        xml_data = get_pubmed_paper(p.pmid)
        context.update(get_pubmed_paper_context(p.pmid, xml_data))
        context.update(get_paper_references_context(p, xml_data))

    return render(request, "papers/detail_min.html", context)


@ratelimit(key="ip", rate=rl_rate, block=rl_block)
def datasets(request, paper_id):
    p = get_object_or_404(Paper, pk=paper_id)
    datasets_values = p.datasets.all_valid().values(
        dataset_id=F("id"),
        dataset_paper_name=F("paper__systematic_name"),
        dataset_phenotype_name=F("phenotype__name"),
        dataset_conditionset_name=F("conditionset__display_name"),
        dataset_medium_name=F("medium__display_name"),
        dataset_collection_name=F("collection__shortname"),
        dataset_data_name=F("data_available__name"),
    )
    context = {
        "paper_id": paper_id,
        "paper_systematic_name": p.systematic_name,
        "paper_datasets": datasets_values,
    }
    return render(request, "papers/datasets_min.html", context)


@ratelimit(key="ip", rate=rl_rate, block=rl_block)
def datasets_list(request, paper_id, pmid):
    p = get_object_or_404(Paper, pk=paper_id)

    txt = "\n".join([(u"%s\t%s" % (d.id, d.name)) for d in p.datasets.all()])

    response = HttpResponse(txt, content_type="text/plain")
    response[
        "Content-Disposition"
    ] = 'attachment; filename="%s_%d_datasets_list.txt"' % (
        settings.DOWNLOAD_PREFIX,
        pmid,
    )

    return response
