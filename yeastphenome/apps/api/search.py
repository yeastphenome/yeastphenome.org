from django.conf import settings

from yeastphenome.apps.papers.search import run_search_tag_query as papers_search
from yeastphenome.apps.datasets.search import run_search_tag_query as dataset_search
from yeastphenome.apps.phenotypes.search import (
    run_search_tag_query as phenotypes_search,
)
from yeastphenome.apps.conditions.search import (
    run_search_tag_query as conditions_search,
)

from rest_framework.renderers import JSONRenderer
from ratelimit.mixins import RatelimitMixin

from rest_framework.response import Response
from rest_framework.views import APIView
import json


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
