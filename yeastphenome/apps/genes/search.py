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
            Gene.objects.exclude(systematic_name=None)
            .values_list("systematic_name", flat=True)
            .distinct(),
            Gene.objects.exclude(common_name=None)
            .values_list("common_name", flat=True)
            .distinct(),
            GeneAlias.objects.exclude(name=None)
            .values_list("name", flat=True)
            .distinct(),
        )
    )

    return [{"value": x, "icon": "🏷️", "code": "query"} for x in names if x]


def run_gene_search_tag_query(queries):
    """The equivalent search for genes, however we don't have specific fields to search."""

    queries = queries or []
    queryset = Gene.all()

    for query in queries:
        query = escape_regex(query)
        queryset = queryset.filter(
            Q(systematic_name__iregex=query)
            | Q(common_name__iregex=query)
            | Q(primary_sgdid__iregex=query)
            | Q(aliases__name__iregex=query)
        ).distinct()
    return queryset
