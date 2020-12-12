from django.db.models import Q

from yeastphenome.apps.common.utils import escape_regex
from yeastphenome.apps.phenotypes.models import Phenotype
from yeastphenome.apps.conditions.models import Medium, ConditionType, ConditionSet
from yeastphenome.apps.datasets.models import (
    Dataset,
    Datatype,
    Tag,
    Collection,
)


import itertools

def get_search_tags():
    """Return a list of gene search tags, which we do all as queries."""

    # Systematic names, common names, and aliases
    names = set(
        itertools.chain(
            Gene.objects.values_list("systematic_name", flat=True),
            Gene.objects.values_list("common_name", flat=True),
            GeneAlias.objects.values_list("name", flat=True),
        )
    )

    # Remove empty values and sort in alphabetical order
    names.discard(None)
    names = sorted(names)

    return [{"value": x, "icon": "🏷️", "code": "query"} for x in names if x]


def run_search_tag_query(queries, collection=None):
    """this function is called from the papers/views.py for the explorer function
    It takes in a list of tags (and associated models) to build a query for datasets.
    """
    queries = queries or []
    queryset = Dataset.all()

    if collection:
        queryset = queryset.filter(collection=collection)

    for query in queries:
        query = escape_regex(query)
        queryset = queryset.filter(
            Q(name__iregex=query)
            | Q(phenotype__name__iregex=query)
            | Q(collection__name__iregex=query)
            | Q(medium__display_name__iregex=query)
            | Q(conditionset__conditions__type__name__iregex=query)
        ).distinct()

    return queryset
