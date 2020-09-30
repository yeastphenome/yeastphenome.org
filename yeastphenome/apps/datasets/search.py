from django.db.models import Q

from yeastphenome.apps.phenotypes.models import Phenotype
from yeastphenome.apps.conditions.models import Medium, Condition
from yeastphenome.apps.datasets.models import Dataset, Datatype, Tag, Collection

# Search functions


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
        {"value": x[0], "icon": "🏷️", "code": "tag"}
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
    It takes in a list of tags (and associated models) to build a query for papers.
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
    tag_query = Q()
    collection_query = Q()
    datatype_query = Q()
    medium_query = Q()
    phenotype_query = Q()
    conditions_query = Q()

    if "tag" in tags:
        tag_query = Q(tags__name__in=tags["tag"])

    if "collection" in tags:
        collection_query = Q(collection__name__in=tags["collection"])

    # Only query for data available, data_published / data_measured not useful
    if "datatype" in tags:
        datatype_query = Q(data_available__name__in=tags["datatype"])

    if "medium" in tags:
        medium_query = Q(medium__display_name__in=tags["medium"])

    if "phenotype" in tags:
        phenotype_query = Q(phenotype__name__in=tags["phenotype"])

    if "conditions" in tags:
        print(tags)
        conditions_query = Q(
            conditionset__conditions__type__name__iregex="(%s)"
            % "|".join(tags["conditions"])
        )

    results = queryset.filter(
        tag_query,
        collection_query,
        datatype_query,
        medium_query,
        phenotype_query,
        conditions_query,
    )

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
