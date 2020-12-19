from django.db.models import Q

from yeastphenome.apps.common.utils import escape_regex
from yeastphenome.apps.genes.models import (
    Gene,
    GeneAlias,
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


def run_search_tag_query(queries):
    """The equivalent search for genes, however we don't have specific fields to search."""

    queries = queries or []
    queryset = Gene.all_valid()

    for query in queries:
        query = escape_regex(query)
        queryset = queryset.filter(
            Q(systematic_name__iregex=query)
            | Q(common_name__iregex=query)
            | Q(primary_sgdid__iregex=query)
            | Q(aliases__name__iregex=query)
        ).distinct()
    return queryset
