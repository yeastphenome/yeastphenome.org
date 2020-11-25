from django.db.models import Q

from yeastphenome.apps.phenotypes.models import Phenotype
from yeastphenome.apps.conditions.models import Medium, Condition
from yeastphenome.apps.datasets.models import (
    Dataset,
    Datatype,
    Tag,
    Collection,
    Gene,
    GeneAlias,
)

# Search functions


def get_gene_search_tags():
    """Return a list of gene search tags, which we do all as queries."""

    # Systematic names
    systematic_names = [
        {"value": x, "icon": "🏷️", "code": "query"}
        for x in Gene.objects.exclude(systematic_name=None)
        .values_list("systematic_name", flat=True)
        .distinct()
    ]

    # Common Names
    common_names = [
        {"value": x, "icon": "🏷️", "code": "query"}
        for x in Gene.objects.exclude(common_name=None)
        .values_list("common_name", flat=True)
        .distinct()
    ]

    # Aliases
    aliases = [
        {"value": x, "icon": "🏷️", "code": "query"}
        for x in GeneAlias.objects.exclude(name=None)
        .values_list("name", flat=True)
        .distinct()
    ]
    return systematic_names + common_names + aliases


def get_search_tags():
    """Return a list of tags, each with a name and icon, to return to the
    data explorer tag search
    """
    # DataTypes
    datatypes = [
        {"value": x[0], "icon": "💽", "code": "datatype"}
        for x in Datatype.objects.values_list("name").distinct()
    ]

    # Tags
    tags = [
        {"value": x[0], "icon": "🏷️", "code": "tags"}
        for x in Tag.objects.values_list("name").distinct()
    ]

    # Phenotypes
    phenotypes = [
        {"value": x[0], "icon": "🐶", "code": "phenotype"}
        for x in Phenotype.objects.values_list("name").distinct()
    ]

    # Condition Sets
    conditions = [
        {"value": x[0], "icon": "🌨️", "code": "conditions"}
        for x in Condition.objects.values_list("type__name").distinct()
    ]

    # Mediums
    mediums = [
        {"value": x[0], "icon": "🧫", "code": "medium"}
        for x in Medium.objects.values_list("display_name").distinct()
    ]

    # Collections
    collections = [
        {"value": x[0], "icon": "🏺", "code": "collection"}
        for x in Collection.objects.values_list("name").distinct()
    ]

    return datatypes + tags + collections + mediums + phenotypes + conditions


def run_search_tag_query(query, taglist=None, return_instances=False, collection=None):
    """this function is called from the papers/views.py for the explorer function
    It takes in a list of tags (and associated models) to build a query for datasets.
    """
    # First do a search based on the tags, assemble those of liked kind. A tag without
    # a code is part of the list of queries
    queries = [] if not query else [query]
    tags = {}
    for tag in taglist or []:
        if tag["code"] in ["", "query"]:
            queries.append(tag["value"])
        else:
            if tag["code"] not in tags:
                tags[tag["code"]] = []
            tags[tag["code"]].append(tag["value"])

    queryset = Dataset.objects.exclude(
        paper__latest_data_status__status__name="not relevant"
    ).distinct()

    # Filter to specific collection
    if collection:
        queryset = queryset.filter(collection=collection)

    # Prepare querysets

    all_queries = Q()
    if "tags" in tags:
        for tag in tags["tags"]:
            all_queries = all_queries & Q(tags__name__iregex=tag)

    if "collection" in tags:
        for tag in tags["collection"]:
            all_queries = all_queries & Q(collection__name__iregex=tag)

    # Only query for data available, data_published / data_measured not useful
    if "datatype" in tags:
        for tag in tags["datatype"]:
            all_queries = all_queries & Q(data_available__name__iregex=tag)

    if "medium" in tags:
        for tag in tags["medium"]:
            all_queries = all_queries & Q(medium__display_name__iregex=tag)

    if "phenotype" in tags:
        for tag in tags["phenotype"]:
            all_queries = all_queries & Q(phenotype__name__iregex=tag)

    if "conditions" in tags:
        for tag in tags["conditions"]:
            all_queries = all_queries & Q(
                conditionset__conditions__type__name__iregex=tag
            )

    results = queryset.filter(all_queries)

    # Now filter down results more, search all fields for query if defined
    if queries:
        queries = "(%s)" % "|".join(queries)
        results = results.filter(
            Q(name__iregex=queries)
            | Q(phenotype__name__iregex=queries)
            | Q(collection__name__iregex=queries)
            | Q(medium__systematic_name__iregex=queries)
            | Q(conditionset__conditions__type__name__iregex=queries)
        ).distinct()

    if return_instances is True:
        return results

    return {
        # (dataset_id, data_available, paper id, first author, last author, date published, phenotype_observable_name, reporter, conditionset, medium, collection, data_published_name)
        # (1, 3, 2, 'Chan TF', 'Zheng XF', 2000, 'growth', 'streaks on agar', 'sirolimus [25 nM]', 'YPD', 'hap a', 'discrete', 2222)
        "results": list(
            # Exclude results without data available
            results.exclude(data_available=None).values_list(
                "id",
                "data_available",
                "paper__id",
                "paper__first_author",
                "paper__last_author",
                "paper__pub_date",
                "phenotype__observable__name",
                "phenotype__reporter",
                "conditionset__display_name",
                "medium__display_name",
                "collection__shortname",
                "data_published__name",
                "tested_num",
                "phenotype__id",  # 13-16
                "conditionset__id",
                "medium__id",
                "collection__id",
            )
        ),
        "count": results.count(),
        "datatypes": {x[0]: x[1] for x in Datatype.objects.values_list("id", "name")},
    }


def run_gene_search_tag_query(query):
    """The equivalent search for genes, however we don't have specific fields to search."""
    queries = [] if not query else query
    if not isinstance(queries, list):
        queries = [queries]

    # For genes, we do a single query wit
    queryset = Gene.objects.all()

    # Now filter down results more, search all fields for query if defined
    queries = "(%s)" % "|".join(queries)
    results = queryset.filter(
        Q(systematic_name__iregex=queries)
        | Q(common_name__iregex=queries)
        | Q(primary_sgdid__iregex=queries)
        | Q(aliases__name__iregex=queries)
    ).distinct()
    return results
