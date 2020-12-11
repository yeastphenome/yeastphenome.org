from django.views import generic
from django.shortcuts import render, reverse

from django.views.decorators.cache import never_cache

from .models import Paper
from .utils import (
    get_pubmed_paper_context,
    get_pubmed_paper,
    get_paper_references_context,
)

from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.conf import settings

from ratelimit.mixins import RatelimitMixin
from ratelimit.decorators import ratelimit
from yeastphenome.apps.papers.search import get_search_tags

from yeastphenome.settings import (
    VIEW_RATE_LIMIT as rl_rate,
    VIEW_RATE_LIMIT_BLOCK as rl_block,
)


@never_cache
@ratelimit(key="ip", rate=rl_rate, block=rl_block)
def paper_explorer(request, year=None):
    """Return a paginated list of papers with the data explorer."""
    taglist = []
    links = [
        {"url": reverse("common:explorer"), "name": "Explore data"},
        {"url": reverse("papers:all"), "name": "Papers"},
    ]
    for tag in request.GET.get("query", "").split("|"):
        if not tag:
            continue
        taglist.append({"value": tag, "code": "query"})

    return render(
        request,
        "papers/explorer.html",
        {
            "year": year,
            "taglist": taglist,
            "tags": get_search_tags(),
            "links": links,
            "active": "explorer",
        },
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
            {"url": reverse("common:explorer"), "name": "Explore data"},
            {"url": reverse("papers:all"), "name": "Papers"},
            {
                "url": reverse("papers:detail", args=[paper.id]),
                "name": str(paper),
            },
        ]

        context["DOWNLOAD_PREFIX"] = settings.DOWNLOAD_PREFIX
        context["USER_AUTH"] = self.request.user.is_authenticated
        context["module"] = "papers"
        context["id"] = paper.id
        context["active"] = "explorer"

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


@ratelimit(key="ip", rate=rl_rate, block=rl_block)
def paper_datasets(request, paper_id, pmid):
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
