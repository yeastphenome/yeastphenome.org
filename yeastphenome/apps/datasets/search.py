from django.db.models import Q

from yeastphenome.apps.phenotypes.models import Phenotype
from yeastphenome.apps.conditions.models import ConditionSet, Medium
from yeastphenome.apps.datasets.models import Dataset, Datatype, Gene, Tag, Collection

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

    # Genes
    genes = [
        {"value": x[0], "icon": "🧬", "code": "gene"}
        for x in Gene.objects.values_list("systematic_name").distinct()
    ]

    # Phenotypes
    phenotypes = [
        {"value": x[0], "icon": "🐶", "code": "medium"}
        for x in Phenotype.objects.values_list("name").distinct()
    ]

    # Condition Sets
    conditions = [
        {"value": x[0], "icon": "🌨️", "code": "conditionset"}
        for x in ConditionSet.objects.values_list("systematic_name").distinct()
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

    return datatypes + tags + genes + collections + mediums + phenotypes + conditions


def run_search_tag_query(query, taglist=None, return_instances=False, collection=None):
    """this function is called from the papers/views.py for the explorer function
       It takes in a list of tags (and associated models) to build a query for papers.
    """
    # First do a search based on the tags, assemble those of liked kind
    tags = {}
    for tag in taglist or []:
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
    gene_query = Q()
    collection_query = Q()
    datatype_query = Q()
    medium_query = Q()
    phenotype_query = Q()
    conditionset_query = Q()

    if "tag" in tags:
        tag_query = Q(tags__name__in=tags["tag"])

    if "gene" in tags:
        gene_query = Q(data__gene__systematic_name__in=tags["gene"])

    if "collection" in tags:
        collection_query = Q(collection__name__in=tags["collection"])

    # Only query for data available, data_published / data_measured not useful
    if "datatype" in tags:
        datatype_query = Q(data_available__name__in=tags["datatype"])

    if "medium" in tags:
        medium_query = Q(medium__display_name__in=tags["medium"])

    if "phenotype" in tags:
        phenotype_query = Q(phenotype__name__in=tags["phenotype"])

    if "conditionset" in tags:
        conditionset_query = Q(conditionset__systematic_name__in=tags["conditionset"])

    results = queryset.filter(
        tag_query,
        gene_query,
        collection_query,
        datatype_query,
        medium_query,
        phenotype_query,
        conditionset_query,
    )

    # Now filter down results more, search all fields for query if defined
    if query not in ["", None]:
        results = results.filter(
            Q(name__icontains=query)
            | Q(phenotype__name__icontains=query)
            | Q(collection__name__icontains=query)
            | Q(medium__systematic_name__icontains=query)
            | Q(conditionset__systematic_name__icontains=query)
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
