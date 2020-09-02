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
# from yeastphenome.apps.datasets.models import Dataset

from .permissions import IsStaffOrSuperUser

from rest_framework import serializers, viewsets
from rest_framework.renderers import JSONRenderer
from ratelimit.mixins import RatelimitMixin

from rest_framework.response import Response
from rest_framework.views import APIView
import json

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
    """A search to take a query, and filter by specific tags
    """

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
            ] = "There was an issue parsing your query! Please <a href='https://github.com/yeastphenome/yeastphenome.org/issues'>submit a ticket</a>"
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
    """Given a paper id, get all references for it to populate a graph.
    """

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
