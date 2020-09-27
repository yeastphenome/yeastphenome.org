from django.conf import settings

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
# from yeastphenome.apps.phenotypes.models import Phenotype
from yeastphenome.apps.datasets.models import Gene

from .permissions import IsStaffOrSuperUser

from rest_framework import serializers, viewsets
from rest_framework.renderers import JSONRenderer
from ratelimit.mixins import RatelimitMixin

from rest_framework.response import Response
from rest_framework.views import APIView
import json


# Genes


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
