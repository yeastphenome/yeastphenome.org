from django.db.models import Q

# from yeastphenome.apps.papers.models import Paper
from yeastphenome.apps.phenotypes.models import Phenotype
from yeastphenome.apps.conditions.models import ConditionSet, Medium
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

    # Genes 🧬

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

    return datatypes + tags + collections + mediums + phenotypes + conditions


def run_search_tag_query(query, taglist=None):
    """this function is called from the common/views.py for the explorer function
       It takes in a list of tags (and associated models) to build a query. E.g.:
       [{'value': 'human protein', 'icon': '🏷️', 'code': 'tag', 'style': '--tag-bg:hsl(108,45%,65%)'}, {'value': 'hap a/hap alpha/hom', 'icon': '🏺', 'code': 'collection', 'style': '--tag-bg:hsl(267,63%,69%)'}, {'value': 'haploid MatA', 'icon': '🏺', 'code': 'collection', 'style': '--tag-bg:hsl(24,51%,69%)'}]
       The function here must know how to map the code (e.g., Collection) to a model to search
    """
    # First do a search based on the tags, assemble those of liked kind
    tags = {}
    for tag in taglist or []:
        if tag["code"] not in tags:
            tags[tag["code"]] = []
        tags[tag["code"]].append(tag["value"])

    # Prepare querysets
    tag_query = Q()
    collection_query = Q()
    datatype_query = Q()
    medium_query = Q()
    phenotype_query = Q()
    conditionset_query = Q()

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

    if "conditionset" in tags:
        conditionset_query = Q(conditionset__systematic_name__icontains=query)

    results = Dataset.objects.all().filter(
        tag_query,
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
            | Q(paper__data_abstract__icontains=query)
            | Q(paper__notes__icontains=query)
            | Q(medium__systematic_name__icontains=query)
            | Q(conditionset__systematic_name__icontains=query)
        )

    return {
        "results": list(
            results.values_list(
                "id",
                "name",
                "collection__name",
                "data_published__name",
                "paper__id",
                "tags__name",
            )
        ),
        "count": results.count(),
    }
