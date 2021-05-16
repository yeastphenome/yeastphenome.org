from django.conf import settings
from django.contrib.postgres.aggregates.general import StringAgg
from django.shortcuts import reverse

from yeastphenome.apps.papers.models import Paper
from yeastphenome.apps.papers.templatetags.my_filters import join_and_more
from yeastphenome.apps.papers.search import run_search_tag_query as papers_search

from rest_framework.renderers import JSONRenderer
from ratelimit.mixins import RatelimitMixin

from rest_framework.response import Response
from rest_framework.views import APIView
from .datasets import generate_datasets


# Papers Query


class RunPapersQuery(RatelimitMixin, APIView):
    """server side render of papers query"""

    ratelimit_key = "ip"
    ratelimit_rate = settings.VIEW_RATE_LIMIT
    ratelimit_block = settings.VIEW_RATE_LIMIT_BLOCK
    ratelimit_method = "GET"
    renderer_classes = (JSONRenderer,)

    def get(self, request, year=None):
        print("GET RunPapersQuery")

        # Start and length to return
        start = int(request.GET["start"])
        length = int(request.GET["length"])
        draw = int(request.GET["draw"])

        # Order column and direction
        # Important: columns 2 (phenotypes) and 3 (papers) doesn't have a simple filter solution
        order = request.GET["order[0][column]"]
        direction = request.GET["order[0][dir]"]  # asc or desc
        order_lookup = {
            "0asc": "first_author",
            "0desc": "-first_author",
            "1asc": "phenotype_list",
            "1desc": "-phenotype_list",
            "2asc": "condition_list",
            "2desc": "-condition_list",
        }

        # Empty datatable
        data = {"draw": draw, "recordsTotal": 0, "recordsFiltered": 0, "data": []}
        queryset = []
        taglist = []
        count = 0

        taglist = request.GET.get("query", "").split("|")
        if taglist:
            queryset = papers_search(taglist)
            count = queryset.count()

        # Filter to year, if defined
        if year is not None and queryset:
            queryset = queryset.filter(pub_date=year)
            count = queryset.count()

        if queryset:
            agg_field = "datasets__phenotype__observable__name"
            queryset = queryset.annotate(
                phenotype_list=StringAgg(
                    agg_field, delimiter="; ", distinct=True, ordering=agg_field
                )
            )

            agg_field = "datasets__conditionset__conditions__type__name"
            queryset = queryset.annotate(
                condition_list=StringAgg(
                    agg_field, delimiter="; ", distinct=True, ordering=agg_field
                )
            )

        order_by = "%s%s" % (order, direction)
        if order_by in order_lookup and queryset:
            print(f"Ordering by {order_by}")
            queryset = queryset.order_by(order_lookup[order_by])
            count = queryset.count()

        if start > count:
            start = 0
        end = start + length - 1

        # If we've gone too far
        if end > count:
            end = count - 1

        queryset = queryset[start : end + 1]
        data["recordsTotal"] = count
        data["recordsFiltered"] = count

        for paper in queryset:
            data["data"].append(
                [
                    '<a href="%s">%s</a></td>'
                    % (reverse("papers:detail", args=[paper.pk]), paper),
                    join_and_more(paper.phenotype_list.split("; "), 7),
                    join_and_more(paper.condition_list.split("; "), 7),
                ]
            )
        return Response(status=200, data=data)


# Paper Datasets


class GetPaperDatasets(RatelimitMixin, APIView):
    """Given a paper, serialize the datasets."""

    ratelimit_key = "ip"
    ratelimit_rate = settings.VIEW_RATE_LIMIT
    ratelimit_block = settings.VIEW_RATE_LIMIT_BLOCK
    ratelimit_method = "GET"
    renderer_classes = (JSONRenderer,)

    def get(self, request, paper_id):
        print("GET GetPaperdatasets")

        # Start and length to return
        draw = int(request.GET["draw"])

        # Empty datatable
        data = {"draw": draw, "recordsTotal": 0, "recordsFiltered": 0, "data": []}

        try:
            paper = Paper.objects.get(id=paper_id)
        except Paper.DoesNotExist:
            return Response(status=200, data=data)
        datasets = (
            paper.datasets.select_related("phenotype__observable")
            .select_related("collection")
            .select_related("conditionset")
            .all()
        )

        data = generate_datasets(request, data, datasets)

        # Must make model json serializable
        return Response(status=200, data=data)
