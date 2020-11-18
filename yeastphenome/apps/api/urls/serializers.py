from django.conf import settings
from decimal import Decimal

from yeastphenome.apps.papers.models import Paper

from yeastphenome.apps.datasets.models import Dataset
from yeastphenome.apps.papers.utils import get_paper_references_context
from yeastphenome.apps.papers.search import run_search_tag_query as papers_search
from yeastphenome.apps.datasets.search import run_search_tag_query as dataset_search
from yeastphenome.apps.phenotypes.search import (
    run_search_tag_query as phenotypes_search,
)
from yeastphenome.apps.conditions.search import (
    run_search_tag_query as conditions_search,
)

# from yeastphenome.apps.conditions.models import ConditionSet, ConditionType
from yeastphenome.apps.phenotypes.models import Observable
from yeastphenome.apps.datasets.models import Gene, Data
from yeastphenome.apps.conditions.models import (
    Tag as ConditionTag,
    ConditionType,
    Medium,
)

from .permissions import IsStaffOrSuperUser

from rest_framework import serializers, viewsets
from rest_framework.renderers import JSONRenderer
from ratelimit.mixins import RatelimitMixin

from rest_framework.response import Response
from rest_framework.views import APIView
from django.db.models import Q, Count
import json


# Helper Function to generate Dataset Cart buttons
def generate_datasets(request, data, datasets, query=None):
    """A shared view to take a request, and the started data, and generate
    the listing.
    """
    # Start and length to return
    start = int(request.GET["start"])
    length = int(request.GET["length"])
    query = request.GET["search[value]"]
    cart = request.session.get("cart", [])

    # If there is a filter
    if query:
        try:
            f = (
                Q(id=int(query))
                | Q(name__icontains=query)
                | Q(tags__name__icontains=query)
                | Q(collection__shortname__icontains=query)
                | Q(conditionset__display_name__icontains=query)
                | Q(paper__first_author__icontains=query)
                | Q(paper__last_author__icontains=query)
                | Q(phenotype__name__icontains=query)
                | Q(medium__display_name__icontains=query)
                | Q(phenotype__reporter__icontains=query)
                | Q(data_available__name__icontains=query)
            )
            datasets = datasets.filter(f).distinct()
        except:
            f = (
                Q(name__icontains=query)
                | Q(tags__name__icontains=query)
                | Q(collection__shortname__icontains=query)
                | Q(conditionset__display_name__icontains=query)
                | Q(paper__first_author__icontains=query)
                | Q(paper__last_author__icontains=query)
                | Q(phenotype__name__icontains=query)
                | Q(medium__display_name__icontains=query)
                | Q(phenotype__reporter__icontains=query)
                | Q(data_available__name__icontains=query)
            )
            datasets = datasets.filter(f).distinct()

    order = request.GET["order[0][column]"]
    direction = request.GET["order[0][dir]"]  # asc or desc
    order_lookup = {
        "0asc": "id",
        "0desc": "-id",
        "1asc": "paper__first_author",
        "1desc": "-paper__first_author",
        "2asc": "phenotype__name",
        "2desc": "-phenotype__name",
        "3asc": "conditionset__display_name",
        "3desc": "-conditionset__display_name",
        "4asc": "medium__display_name",
        "4desc": "-medium__display_name",
        "5asc": "collection__shortname",
        "5desc": "-collection__shortname",
        "6asc": "data_available",
        "6desc": "-data_available",
    }

    order_by = "%s%s" % (order, direction)
    if order_by in order_lookup:
        print(f"Ordering by {order_by}")

        # Some datasets don't have a conditionset, or medium will issue an error
        if order_by in ["3asc", "3desc"]:
            datasets = datasets.exclude(conditionset=None)
        elif order_by in ["4asc", "4desc"]:
            datasets = datasets.exclude(medium=None)
        elif order_by in ["5asc", "5desc"]:
            datasets = datasets.exclude(collection=None)
        datasets = datasets.order_by(order_lookup[order_by])

    count = datasets.count()
    if start > count:
        start = count - start
    end = start + length

    # If we've gone too far
    if end > count:
        end = count - 1

    datasets = datasets[start : end + 1]
    data["recordsTotal"] = count
    data["recordsFiltered"] = count

    # Since we have a small queryset (25) we can loop over without it being too slow
    for dataset in datasets:

        if dataset.id not in cart:
            button = (
                '<button id="dataset-cart-%s" type="button" class="btn btn-primary btn-sm add-to-cart" style="width:120px" data-id="%s">Add</button>'
                % (dataset.id, dataset.id)
            )
        else:
            button = (
                '<button id="dataset-cart-%s" type="button" class="btn btn-danger btn-sm remove-from-cart" data-id="%s" style="width:120px">Remove</button>'
                % (dataset.id, dataset.id)
            )

        data["data"].append(
            [
                "<input id='%s' type='hidden' name='%s'><a id='%s' href='/datasets/%s'>%s</a>"
                % (dataset.id, dataset.id, dataset.id, dataset.id, dataset.id),
                str(dataset.paper),
                dataset.phenotype.name,
                getattr(dataset.conditionset, "display_name", ""),
                getattr(dataset.medium, "display_name", ""),
                getattr(dataset.collection, "shortname", ""),
                str(dataset.data_available or ""),
                button,
            ]
        )

    return data


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


# Datasets in Cart


class GetCartDatasets(RatelimitMixin, APIView):
    """Given a medium, serialize the datasets for a DataTable."""

    ratelimit_key = "ip"
    ratelimit_rate = settings.VIEW_RATE_LIMIT
    ratelimit_block = settings.VIEW_RATE_LIMIT_BLOCK
    ratelimit_method = "GET"
    renderer_classes = (JSONRenderer,)

    def get(self, request):
        print("GET GetMediumDatasets")

        # Start and length to return
        draw = int(request.GET["draw"])

        # Empty datatable
        data = {"draw": draw, "recordsTotal": 0, "recordsFiltered": 0, "data": []}
        cart = request.session.get("cart", [])
        datasets = Dataset.objects.filter(id__in=cart)
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


# Genes


class GetGeneDatasets(RatelimitMixin, APIView):
    """Given a gene serialize the datasets for a DataTable"""

    ratelimit_key = "ip"
    ratelimit_rate = settings.VIEW_RATE_LIMIT
    ratelimit_block = settings.VIEW_RATE_LIMIT_BLOCK
    ratelimit_method = "GET"
    renderer_classes = (JSONRenderer,)

    def get(self, request, systematic_name):
        print("GET GetGeneDatasets")

        # Start and length to return
        start = int(request.GET["start"])
        length = int(request.GET["length"])
        draw = int(request.GET["draw"])
        query = request.GET["search[value]"]

        # Empty datatable
        data = {"draw": draw, "recordsTotal": 0, "recordsFiltered": 0, "data": []}

        try:
            gene = Gene.objects.get(
                Q(systematic_name__iexact=systematic_name)
                | Q(common_name__iexact=systematic_name)
            )
        except Gene.DoesNotExist:
            return Response(status=200, data=data)

        datasets = (
            Data.objects.filter(gene=gene)
            .exclude(Q(value=None) | Q(value=Decimal("NaN")))
            .order_by("-value")
        )

        # If there is a filter
        if query:
            f = Q(dataset__name__icontains=query)
            datasets = datasets.filter(f).distinct()

        count = datasets.count()
        ranks = [(1 - (idx / count)) * 100 for idx, sim in enumerate(datasets)]
        if start > count:
            start = count - start
        end = start + length

        # If we've gone too far
        if end > count:
            end = count - 1

        datasets = datasets[start : end + 1]
        ranks = ranks[start : end + 1]
        data["recordsTotal"] = count
        data["recordsFiltered"] = count

        # Since we have a small queryset (25) we can loop over without it being too slow
        for i, dataset in enumerate(datasets):
            data["data"].append(
                [
                    "<a href='/datasets/%s'>%s</a>"
                    % (dataset.dataset.id, dataset.dataset.name),
                    round(dataset.value, 1),
                    round(ranks[i], 1),
                ]
            )

        # Must make model json serializable
        return Response(status=200, data=data)


class GetSimilarGenes(RatelimitMixin, APIView):
    """Given A gene systematic name, return ordered list of similarity scores
    (most to least similar), top N for each
    """

    ratelimit_key = "ip"
    ratelimit_rate = settings.VIEW_RATE_LIMIT
    ratelimit_block = settings.VIEW_RATE_LIMIT_BLOCK
    ratelimit_method = "GET"
    renderer_classes = (JSONRenderer,)

    def get(self, request, systematic_name, N=10, reverse=0):
        print("GET GetSimilarGenes")
        try:
            gene = Gene.objects.get(systematic_name=systematic_name)
        except Gene.DoesNotExist:
            return Response(status=404)

        # Only get top and bottom N
        sims = list(gene.get_ranked_similar(reverse=(reverse == 1)))
        first_n = sims[:N]
        last_n = sims[len(sims) - N :]

        scores = {}
        for sim in first_n + last_n:
            if sim.gene1.systematic_name == gene.systematic_name:
                scores[sim.gene2.systematic_name] = {
                    "score": sim.score,
                    "pvalue": sim.pvalue,
                }
            else:
                scores[sim.gene1.systematic_name] = {
                    "score": sim.score,
                    "pvalue": sim.pvalue,
                }

        # Must make model json serializable
        return Response(status=200, data=scores)


class GetGenes(RatelimitMixin, APIView):
    """Return a list of all genes"""

    ratelimit_key = "ip"
    ratelimit_rate = settings.VIEW_RATE_LIMIT
    ratelimit_block = settings.VIEW_RATE_LIMIT_BLOCK
    ratelimit_method = "GET"
    renderer_classes = (JSONRenderer,)

    def get(self, request):
        print("GET GetGenes")
        genes = list(Gene.objects.values_list("systematic_name", flat=True).distinct())
        return Response(status=200, data=genes)


# Papers


class PaperSerializer(serializers.ModelSerializer):

    label = serializers.SerializerMethodField("get_label")

    def get_label(self, instance):
        return "paper"

    class Meta:
        model = Paper
        fields = (
            "id",
            "first_author",
            "last_author",
            "pub_date",
            "pmid",
            "modified_on",
            "data_abstract",
            "label",
        )


class PaperViewSet(viewsets.ModelViewSet):
    def get_queryset(self):
        return Paper.objects.all()

    serializer_class = PaperSerializer
    permission_classes = (IsStaffOrSuperUser,)


# Search


class BaseSearch(RatelimitMixin, APIView):
    """A search to take a query, and filter by specific tags"""

    ratelimit_key = "ip"
    ratelimit_rate = settings.VIEW_RATE_LIMIT
    ratelimit_block = settings.VIEW_RATE_LIMIT_BLOCK
    ratelimit_method = "POST"
    renderer_classes = (JSONRenderer,)
    endpoint = "base"

    def get_tags(self, query, tags):
        return {"results": [], "count": 0, "cart": []}

    def post(self, request):
        print(f"POST {self} search")
        query = request.POST.get("query[query]", "")
        tags = request.POST.get("query[tags]", "[]") or "[]"

        # Start of results
        results = {}

        # Load the tags as json
        try:
            tags = json.loads(tags)
            results.update(self.get_tags(query, tags))
        except:
            results[
                "message"
            ] = "There was an issue parsing your query! Please <a target='_blank' href='https://github.com/yeastphenome/yeastphenome.org/issues'>submit a ticket</a>"
            tags = {}
        return Response(status=200, data=results)


class ConditionsSearch(BaseSearch):
    def get_tags(self, query, tags):
        return conditions_search(query, tags)


class DatasetsSearch(BaseSearch):
    def get_tags(self, query, tags):
        return dataset_search(query, tags)


class PapersSearch(BaseSearch):
    def get_tags(self, query, tags):
        return papers_search(query, tags)


class PhenotypesSearch(BaseSearch):
    def get_tags(self, query, tags):
        return phenotypes_search(query, tags)


class GetPaperReferences(RatelimitMixin, APIView):
    """Given a paper id, get all references for it to populate a graph."""

    ratelimit_key = "ip"
    ratelimit_rate = settings.VIEW_RATE_LIMIT
    ratelimit_block = settings.VIEW_RATE_LIMIT_BLOCK
    ratelimit_method = "GET"
    renderer_classes = (JSONRenderer,)

    def get(self, request, paper_id):
        print("GET GetPaperReferences")
        try:
            paper = Paper.objects.get(id=paper_id)
        except Paper.DoesNotExist:
            return Response(status=404)

        # Must make model json serializable
        data = get_paper_references_context(paper)
        data["paper"] = {"pmid": paper.pmid, "name": str(paper), "status": "root"}
        return Response(status=200, data=data)
