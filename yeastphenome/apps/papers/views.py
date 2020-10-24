from django.db.models import Q
from django.views import generic
from django.shortcuts import render, reverse
from django.core.paginator import Paginator

from django.views.decorators.cache import never_cache

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
from yeastphenome.apps.papers.search import get_search_tags, run_search_tag_query

from yeastphenome.settings import (
    VIEW_RATE_LIMIT as rl_rate,
    VIEW_RATE_LIMIT_BLOCK as rl_block,
)


@never_cache
@ratelimit(key="ip", rate=rl_rate, block=rl_block)
def paper_explorer(request, year=None):
    """Return a paginated list of papers with the data explorer."""
    # Count == 0 indicates a search, no search is set to None
    queryset = []
    count = None
    taglist = []
    links = [{"url": reverse("papers:all"), "name": "Paper Explorer"}]
    for key in [
        "conditionset",
        "phenotype",
        "medium",
        "datatype",
        "collection",
        "gene",
        "tag",
        "year",
        "authors",
        "query",
    ]:
        for tag in request.GET.get(key, "").split(","):
            if not tag:
                continue
            taglist.append({"value": tag, "code": key})

    if taglist:
        queryset = run_search_tag_query(query=None, taglist=taglist)

        # 50 results per page
        paginator = Paginator(queryset, 50)
        page = request.GET.get("page")
        queryset = paginator.get_page(page)

        # Filter to year, if defined
        if year is not None:
            queryset = queryset.filter(pub_date=year)
        count = len(queryset)

    queryset = {"results": queryset, "count": count}
    return render(
        request,
        "papers/explorer.html",
        {"queryset": queryset, "tags": get_search_tags(), "links": links},
    )


class PaperDetailView(generic.DetailView, RatelimitMixin):
    model = Paper
    template_name = "papers/detail.html"
    ratelimit_key = "ip"
    ratelimit_rate = rl_rate
    ratelimit_block = rl_block

    def get_context_data(self, **kwargs):
        context = super(PaperDetailView, self).get_context_data(**kwargs)
        paper = context["object"]

        context["links"] = [
            {"url": reverse("papers:all"), "name": "Paper Explorer"},
            {
                "url": reverse("papers:detail", args=[paper.id]),
                "name": "Paper %s" % paper.id,
            },
        ]

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
        context["datasets"] = paginator.get_page(page)
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
    ratelimit_key = "ip"
    ratelimit_rate = rl_rate
    ratelimit_block = rl_block

    def get_context_data(self, **kwargs):
        context = super(ContributorsListView, self).get_context_data(**kwargs)
        papers_list = Paper.objects.filter(
            Q(dataset__data_source__acknowledge=True)
            | Q(dataset__tested_source__acknowledge=True)
        ).distinct()

        # contributors names, lookup with paper id
        context["papers_list"] = papers_list
        context["active"] = "about"
        context["links"] = [
            {"url": reverse("common:about"), "name": "About"},
            {"url": reverse("papers:contributors"), "name": "Paper Contributors"},
        ]

        return context


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
    response[
        "Content-Disposition"
    ] = 'attachment; filename="%s_%d_datasets_list.txt"' % (
        settings.DOWNLOAD_PREFIX,
        p.pmid,
    )

    return response
