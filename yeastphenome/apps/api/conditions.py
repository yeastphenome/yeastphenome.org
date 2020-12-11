from django.conf import settings
from django.contrib.postgres.aggregates.general import StringAgg

from yeastphenome.apps.papers.templatetags.my_filters import join_and_more
from yeastphenome.apps.conditions.search import run_search_tag_query as conditions_query

from yeastphenome.apps.conditions.models import (
    Tag as ConditionTag,
    ConditionType,
    Medium,
)

from rest_framework.renderers import JSONRenderer
from ratelimit.mixins import RatelimitMixin

from rest_framework.response import Response
from rest_framework.views import APIView
from django.db.models import Q, Count

from .datasets import generate_datasets

# Conditions Query


class RunConditionsQuery(RatelimitMixin, APIView):
    """server side render of conditions query"""

    ratelimit_key = "ip"
    ratelimit_rate = settings.VIEW_RATE_LIMIT
    ratelimit_block = settings.VIEW_RATE_LIMIT_BLOCK
    ratelimit_method = "GET"
    renderer_classes = (JSONRenderer,)

    def get(self, request):
        print("GET RunConditionsQuery")

        # Start and length to return
        start = int(request.GET["start"])
        length = int(request.GET["length"])
        draw = int(request.GET["draw"])

        order = request.GET["order[0][column]"]
        direction = request.GET["order[0][dir]"]  # asc or desc
        order_lookup = {
            "0asc": "name",
            "0desc": "-name",
            "1asc": "condition__dose",
            "1desc": "-condition_dose",
            "2asc": "phenotype_list",
            "2desc": "-phenotype_list",
            "3asc": "paper_list",
            "3desc": "-paper_list",
            "4asc": "tag_list",
            "4desc": "-tag_list",
        }

        # Empty datatable
        data = {"draw": draw, "recordsTotal": 0, "recordsFiltered": 0, "data": []}
        queryset = []
        taglist = []
        count = 0

        for key in [
            "pubchem_name",
            "other_name",
            "chebi_name",
            "medium",
            "name",
            "tags",
            "query",
        ]:
            for tag in request.GET.get(key, "").split("|"):
                if not tag:
                    continue
                taglist.append({"value": tag, "code": key})

        if taglist:
            queryset = conditions_query(query=None, taglist=taglist)
            count = len(queryset)

        # Create field to sort phenotypes (2), conditions (3), and tags (4)
        if queryset:
            agg_field = "condition__conditionset__dataset__paper__first_author"
            queryset = queryset.annotate(
                paper_list=StringAgg(
                    agg_field, delimiter=", ", distinct=True, ordering=agg_field
                )
            )
            agg_field = "condition__conditionset__dataset__phenotype__observable__name"
            queryset = queryset.annotate(
                phenotype_list=StringAgg(
                    agg_field, delimiter=", ", distinct=True, ordering=agg_field
                )
            )
            agg_field = "tags__name"
            queryset = queryset.annotate(
                tag_list=StringAgg(
                    agg_field, delimiter=", ", distinct=True, ordering=agg_field
                )
            )

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

        queryset = queryset[start : end + 1]
        data["recordsTotal"] = count
        data["recordsFiltered"] = count

        for ct in queryset:
            data["data"].append(
                [
                    ct.link_detail(),
                    ", ".join([condition.dose for condition in ct.conditions()]),
                    join_and_more(ct.phenotypes(), 7),
                    join_and_more(ct.papers(), 7),
                    ", ".join([tag.name for tag in ct.tags.all()]),
                ]
            )

        # Must make model json serializable
        return Response(status=200, data=data)


# Tag Condition Types


class GetTagConditionTypes(RatelimitMixin, APIView):
    """Given a tag, serialize the associated condition types into a DataTable."""

    ratelimit_key = "ip"
    ratelimit_rate = settings.VIEW_RATE_LIMIT
    ratelimit_block = settings.VIEW_RATE_LIMIT_BLOCK
    ratelimit_method = "GET"
    renderer_classes = (JSONRenderer,)

    def get(self, request, tag_id):
        print("GET GetTagConditionTypes")

        # Start and length to return
        start = int(request.GET["start"])
        length = int(request.GET["length"])
        draw = int(request.GET["draw"])
        query = request.GET["search[value]"]

        # Order column and direction
        order = request.GET["order[0][column]"]
        direction = request.GET["order[0][dir]"]  # asc or desc
        order_lookup = {
            "0asc": "name",
            "0desc": "-name",
            "1asc": "other_names",
            "1desc": "-other_names",
            "2asc": "datasets_count",
            "2desc": "-datasets_count",
        }

        # Empty datatable
        data = {"draw": draw, "recordsTotal": 0, "recordsFiltered": 0, "data": []}

        try:
            tag = ConditionTag.objects.get(id=tag_id)
        except ConditionTag.DoesNotExist:
            return Response(status=200, data=data)

        # Annotate with datasets count for filtering, and to those with > 0 datasets
        queryset = (
            tag.conditiontype_set.all()
            .annotate(datasets_count=Count("condition__conditionset__dataset"))
            .filter(datasets_count__gte=0)
        )

        order_by = "%s%s" % (order, direction)
        ordered = False
        if order_by in order_lookup:
            print(f"Ordering by {order_by}")
            queryset = queryset.order_by(order_lookup[order_by])
            ordered = True

        # If there is a filter
        if query:
            f = (
                Q(name__icontains=query)
                | Q(conditiontype__name__icontains=query)
                | Q(conditiontype__other_names__icontains=query)
            )
            queryset = queryset.filter(f).distinct()

        count = queryset.count()
        if start > count:
            start = count - start
        end = start + length

        # If we've gone too far
        if end > count:
            end = count - 1

        queryset = queryset[start : end + 1]
        data["recordsTotal"] = count
        data["recordsFiltered"] = count

        for ct in queryset:
            data["data"].append(
                [
                    "<a href='/conditions/%s'>%s</a>" % (ct.id, ct.name),
                    ct.other_names or "",
                    ct.datasets_count,
                ]
            )

        # Sort data by datasets count
        def sort_by_count(elem):
            return elem[2]

        # Default ordering to sort by count, if not ordered
        if not ordered:
            data["data"].sort(key=sort_by_count, reverse=True)

        # Must make model json serializable
        return Response(status=200, data=data)


# Condition Type Datasets


class GetConditionTypeDatasets(RatelimitMixin, APIView):
    """Given a condition type, serialize the datasets for a DataTable."""

    ratelimit_key = "ip"
    ratelimit_rate = settings.VIEW_RATE_LIMIT
    ratelimit_block = settings.VIEW_RATE_LIMIT_BLOCK
    ratelimit_method = "GET"
    renderer_classes = (JSONRenderer,)

    def get(self, request, conditiontype_id):
        print("GET GetConditionTypeDatasets")

        # Start and length to return
        draw = int(request.GET["draw"])

        # Empty datatable
        data = {"draw": draw, "recordsTotal": 0, "recordsFiltered": 0, "data": []}

        try:
            ct = ConditionType.objects.get(id=conditiontype_id)
        except ConditionType.DoesNotExist:
            return Response(status=200, data=data)

        datasets = ct.datasets()
        data = generate_datasets(request, data, datasets)

        # Must make model json serializable
        return Response(status=200, data=data)


# Medium Datasets


class GetMediumDatasets(RatelimitMixin, APIView):
    """Given a medium, serialize the datasets for a DataTable."""

    ratelimit_key = "ip"
    ratelimit_rate = settings.VIEW_RATE_LIMIT
    ratelimit_block = settings.VIEW_RATE_LIMIT_BLOCK
    ratelimit_method = "GET"
    renderer_classes = (JSONRenderer,)

    def get(self, request, medium_id):
        print("GET GetMediumDatasets")

        # Start and length to return
        draw = int(request.GET["draw"])

        # Empty datatable
        data = {"draw": draw, "recordsTotal": 0, "recordsFiltered": 0, "data": []}

        try:
            medium = Medium.objects.get(id=medium_id)
        except Medium.DoesNotExist:
            return Response(status=200, data=data)

        datasets = medium.datasets()
        data = generate_datasets(request, data, datasets)

        # Must make model json serializable
        return Response(status=200, data=data)
