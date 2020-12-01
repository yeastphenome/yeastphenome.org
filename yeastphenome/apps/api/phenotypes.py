from django.conf import settings
from django.db.models import Q

from yeastphenome.apps.phenotypes.models import Observable
from yeastphenome.apps.papers.templatetags.my_filters import join_and_more

from rest_framework.renderers import JSONRenderer
from ratelimit.mixins import RatelimitMixin
from django.contrib.postgres.aggregates.general import StringAgg

from rest_framework.response import Response
from rest_framework.views import APIView

from .datasets import generate_datasets
from yeastphenome.apps.phenotypes.search import (
    run_search_tag_query as phenotypes_search,
)

# Observable Datasets


class GetObservableDatasets(RatelimitMixin, APIView):
    """Given an observable, serialize the datasets for a DataTable. This
    is a server side rendering of the datasets table, customized for a phenotype
    to not include the phenotype column.
    """

    ratelimit_key = "ip"
    ratelimit_rate = settings.VIEW_RATE_LIMIT
    ratelimit_block = settings.VIEW_RATE_LIMIT_BLOCK
    ratelimit_method = "GET"
    renderer_classes = (JSONRenderer,)

    def get(self, request, observable_id):
        print("GET GetObservableDatasets")

        # Start and length to return
        draw = int(request.GET["draw"])

        # Empty datatable
        data = {"draw": draw, "recordsTotal": 0, "recordsFiltered": 0, "data": []}

        try:
            observable = Observable.objects.get(id=observable_id)
        except Observable.DoesNotExist:
            return Response(status=200, data=data)

        datasets = observable.datasets()
        data = generate_datasets(request, data, datasets)

        # Must make model json serializable
        return Response(status=200, data=data)


# Phenotypes Query


class RunPhenotypesQuery(RatelimitMixin, APIView):
    """server side render of phenotypes query"""

    ratelimit_key = "ip"
    ratelimit_rate = settings.VIEW_RATE_LIMIT
    ratelimit_block = settings.VIEW_RATE_LIMIT_BLOCK
    ratelimit_method = "GET"
    renderer_classes = (JSONRenderer,)

    def get(self, request):
        print("GET RunPhenotypesQuery")

        # Start and length to return
        start = int(request.GET["start"])
        length = int(request.GET["length"])
        draw = int(request.GET["draw"])
        query = request.GET["search[value]"]

        # Order column and direction
        # Note: we don't have a good way of querying conditions here either, column 1
        # The papers query also warrants annotating by the first paper first author,
        # and sorting on that
        order = request.GET["order[0][column]"]
        direction = request.GET["order[0][dir]"]  # asc or desc
        order_lookup = {
            "0asc": "name",
            "0desc": "-name",
            "1asc": "condition_list",
            "1desc": "-condition_list",
            "2asc": "phenotype__reporter",
            "2desc": "-phenotype__reporter",
            "3asc": "paper_list",
            "3desc": "-paper_list",
        }

        # Empty datatable
        data = {"draw": draw, "recordsTotal": 0, "recordsFiltered": 0, "data": []}
        queryset = []
        taglist = []
        count = 0

        for key in [
            "observable",
            "tags",
            "phenotype",
            "measurement",
            "query",
        ]:
            for tag in request.GET.get(key, "").split(","):
                if not tag:
                    continue
                taglist.append({"value": tag, "code": key})

        if taglist:
            queryset = phenotypes_search(query=None, taglist=taglist)
            count = len(queryset)

        # Create field to conditions (1) and papers (4) - this is not distinct
        if queryset:
            agg_field = "phenotype__dataset__paper__first_author"
            queryset = queryset.annotate(
                paper_list=StringAgg(
                    agg_field, delimiter=", ", distinct=True, ordering=agg_field
                )
            )
            agg_field = "phenotype__dataset__conditionset__conditions__type__name"
            queryset = queryset.annotate(
                condition_list=StringAgg(
                    agg_field, delimiter=", ", distinct=True, ordering=agg_field
                )
            )

        # If there is a filter
        if query and queryset:
            f = (
                Q(name__iregex=query)
                | Q(tags__name__iregex=query)
                | Q(phenotype__name__iregex=query)
                | Q(phenotype__description__iregex=query)
                | Q(phenotype__measurement__name__iregex=query)
                | Q(phenotype__reporter__iregex=query)
            )
            queryset = queryset.filter(f).distinct()
            count = queryset.count()

        order_by = "%s%s" % (order, direction)
        if order_by in order_lookup and queryset:
            print(f"Ordering by {order_by}")
            queryset = queryset.order_by(order_lookup[order_by])
            count = queryset.count()

        if start > count:
            start = count - start
        end = start + length

        # If we've gone too far
        if end > count:
            end = count - 1

        if queryset:
            queryset = queryset[start : end + 1]
        data["recordsTotal"] = count
        data["recordsFiltered"] = count

        for observable in queryset:
            if hasattr(observable, "condition_list"):
                condition_list = join_and_more(observable.condition_list.split(","), 7)
            else:
                condition_list = join_and_more(observable.conditiontypes(), 7)

            data["data"].append(
                [
                    observable.link_detail(),
                    condition_list,
                    join_and_more(observable.reporters(), 7),
                    join_and_more(observable.papers(), 7),
                ]
            )

        # Must make model json serializable
        return Response(status=200, data=data)
