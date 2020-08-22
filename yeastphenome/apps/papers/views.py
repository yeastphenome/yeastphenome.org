from django.db.models import Q
from django.views import generic
from django.shortcuts import render
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger

from .models import Paper
from .utils import (
    get_pubmed_paper_context,
    get_pubmed_paper,
    get_paper_references_context,
)

import os

from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.conf import settings

from ratelimit.mixins import RatelimitMixin
from ratelimit.decorators import ratelimit
from yeastphenome.apps.common.utils import get_papers_by_year
from yeastphenome.settings import (
    VIEW_RATE_LIMIT as rl_rate,
    VIEW_RATE_LIMIT_BLOCK as rl_block,
)


@ratelimit(key="ip", rate=rl_rate, block=rl_block)
def paper_list_view(request):
    """Return a paginated list of papers
    """
    queryset = Paper.objects.all()

    # Exclude the papers marked as "not relevant"
    f = Q(data_statuses__name__exact="not relevant") | Q(
        tested_statuses__name__exact="not relevant"
    )
    queryset = queryset.exclude(f)

    if "q" in request.GET:
        q = request.GET["q"].strip()
        f = (
            Q(first_author__icontains=q)
            | Q(last_author__icontains=q)
            | Q(pmid__contains=q)
        )
        f = f | Q(dataset__phenotype__observable__name__icontains=q)
        f = (
            f
            | Q(dataset__conditionset__conditions__type__name__icontains=q)
            | Q(dataset__conditionset__conditions__type__other_names__icontains=q)
        )
        f = f | Q(dataset__conditionset__conditions__type__chebi_name__icontains=q)
        f = f | Q(dataset__conditionset__conditions__type__pubchem_name__icontains=q)
        f = (
            f
            | Q(dataset__medium__conditions__type__name__icontains=q)
            | Q(dataset__medium__conditions__type__other_names__icontains=q)
        )
        f = f | Q(dataset__medium__conditions__type__chebi_name__icontains=q)
        f = f | Q(dataset__medium__conditions__type__pubchem_name__icontains=q)
        queryset = queryset.filter(f)
    else:
        q = ""

    # 50 results per page
    paginator = Paginator(queryset, 50)
    page = request.GET.get("page")

    context = {
        "paper_counts": get_papers_by_year(),
        "papers_list": paginator.get_page(page),
        "q": q,
    }
    return render(request, "papers/index.html", context)


class PaperDetailView(generic.DetailView, RatelimitMixin):
    model = Paper
    template_name = "papers/detail.html"
    ratelimit_key = "ip"
    ratelimit_rate = rl_rate
    ratelimit_block = rl_block

    def get_context_data(self, **kwargs):
        context = super(PaperDetailView, self).get_context_data(**kwargs)
        paper = context["object"]

        context["DOWNLOAD_PREFIX"] = settings.DOWNLOAD_PREFIX
        context["USER_AUTH"] = self.request.user.is_authenticated

        # Define dataset_set
        dataset_list = (
            paper.dataset_set.select_related("phenotype__observable")
            .select_related("collection")
            .select_related("conditionset")
            .all()
        )
        page = self.request.GET.get("page", 1)
        paginator = Paginator(dataset_list, 50)
        try:
            datasets = paginator.page(page)
        except PageNotAnInteger:
            datasets = paginator.page(1)
        except EmptyPage:
            datasets = paginator.page(paginator.num_pages)

        context["datasets"] = datasets
        context["id"] = paper.id

        # Give credit if credit is due.
        names = paper.acknowledgements_str_list()
        to_acknowledge = []
        if paper.acknowledge_data():
            to_acknowledge.append("the data")
        if paper.acknowledge_tested():
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
        if paper.pmid != 0:
            xml_data = get_pubmed_paper(paper.pmid)
            context.update(get_pubmed_paper_context(paper.pmid, xml_data))
            context.update(get_paper_references_context(paper, xml_data))
        return context


class ContributorsListView(generic.ListView, RatelimitMixin):
    model = Paper
    template_name = "papers/contributors.html"
    context_object_name = "papers_list"
    ratelimit_key = "ip"
    ratelimit_rate = rl_rate
    ratelimit_block = rl_block

    def get_queryset(self):
        return Paper.objects.filter(
            Q(dataset__data_source__acknowledge=True)
            | Q(dataset__tested_source__acknowledge=True)
        ).distinct()


@ratelimit(key="ip", rate=rl_rate, block=rl_block)
def download_zip(request, paper_id, paper_pmid):

    p = get_object_or_404(Paper, pk=paper_id)

    # Check data & tested strains permission status
    permissions_data = list(
        set(p.dataset_set.all().values_list("data_source__release", flat=True))
    )
    permissions_tested = list(
        set(p.dataset_set.all().values_list("tested_source__release", flat=True))
    )

    if all(permissions_data) & all(permissions_tested):
        file_name = os.path.join(settings.DATA_DIR, "%d.zip" % p.pmid)
    else:
        file_name = os.path.join(settings.DATA_DIR, "na.zip")

    file_path = os.path.join(settings.STATIC_ROOT, file_name)

    response = HttpResponse(open(file_path, "rb"), content_type="application/zip")
    response["Content-Disposition"] = 'attachment; filename="%s_%d.zip"' % (
        settings.DOWNLOAD_PREFIX,
        p.pmid,
    )
    return response


@ratelimit(key="ip", rate=rl_rate, block=rl_block)
def paper_datasets(request, paper_id):
    p = get_object_or_404(Paper, pk=paper_id)

    txt = "\n".join([(u"%s\t%s" % (d.id, d.name)) for d in p.dataset_set.all()])

    response = HttpResponse(txt, content_type="text/plain")
    response["Content-Disposition"] = (
        'attachment; filename="%s_%d_datasets_list.txt"'
        % (settings.DOWNLOAD_PREFIX, p.pmid)
    )

    return response
