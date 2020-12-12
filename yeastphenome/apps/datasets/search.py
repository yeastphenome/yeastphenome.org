from django.db.models import Q

from yeastphenome.apps.common.utils import escape_regex
from yeastphenome.apps.phenotypes.models import Phenotype
from yeastphenome.apps.conditions.models import Medium, ConditionType, ConditionSet
from yeastphenome.apps.datasets.models import (
    Dataset,
    Datatype,
    Tag,
    Collection,
    Gene,
    GeneAlias,
)


import itertools


def get_gene_search_tags():
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


def get_search_tags():
    """Return a list of tags, each with a name and icon, to return to the
    data explorer tag search
    """

    tags = set(
        itertools.chain(
            Datatype.objects.values_list("name", flat=True),
            Tag.objects.values_list("name", flat=True),
            Phenotype.objects.values_list("name", flat=True),
            ConditionType.objects.values_list("name", flat=True),
            ConditionType.objects.values_list("chebi_name", flat=True),
            ConditionType.objects.values_list("pubchem_name", flat=True),
            ConditionSet.objects.values_list("display_name", flat=True),
            Medium.objects.values_list("display_name", flat=True),
            Collection.objects.values_list("name", flat=True),
        )
    )

    # Remove empty values and sort in alphabetical order
    tags.discard(None)
    tags = sorted(tags)

    return [{"value": x, "icon": "🏷️", "code": "query"} for x in tags if x]


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
