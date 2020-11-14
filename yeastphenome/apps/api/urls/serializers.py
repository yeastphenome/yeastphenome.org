from django.conf import settings
from decimal import Decimal

from yeastphenome.apps.papers.models import Paper

# from yeastphenome.apps.datasets.models import DataType
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

from .permissions import IsStaffOrSuperUser

from rest_framework import serializers, viewsets
from rest_framework.renderers import JSONRenderer
from ratelimit.mixins import RatelimitMixin

from rest_framework.response import Response
from rest_framework.views import APIView
from django.db.models import Q
import json


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
        start = int(request.GET["start"])
        length = int(request.GET["length"])
        draw = int(request.GET["draw"])
        query = request.GET["search[value]"]

        # Empty datatable
        data = {"draw": draw, "recordsTotal": 0, "recordsFiltered": 0, "data": []}

        try:
            observable = Observable.objects.get(id=observable_id)
        except Observable.DoesNotExist:
            return Response(status=200, data=data)

        datasets = observable.datasets()

        # If there is a filter
        if query:
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
            )
            datasets = datasets.filter(f).distinct()

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
        cart = getattr(request.session, "cart", [])
        for dataset in datasets:

            # Add to downloads checkbox on the left, disabled if not available
            checkbox = '<input id="%s" type="checkbox" name="%s" class="dataset">'
            if not dataset.has_data_in_db:
                checkbox = (
                    '<input id="%s" type="checkbox" name="%s" class="dataset" disabled>'
                )

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

            print(checkbox)
            data["data"].append(
                [
                    "<a href='/datasets/%s'>%s</a>" % (dataset.id, dataset.id),
                    str(dataset.paper),
                    dataset.phenotype.reporter or "",
                    dataset.conditionset.display_name,
                    getattr(dataset.medium, "display_name", ""),
                    dataset.collection.shortname,
                    str(dataset.data_available),
                    button,
                ]
            )

        # This would be alternative (fast) solution that is limited in customization
        # data['data'] = list([list(x) for x in datasets.values_list('id', 'paper', 'phenotype__observable__name', 'phenotype__reporter', 'conditionset__display_name', 'medium__display_name', 'collection__shortname')])

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
