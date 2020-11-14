from django.db.models import Q

# from yeastphenome.apps.papers.models import Paper
from yeastphenome.apps.phenotypes.models import Phenotype
from yeastphenome.apps.conditions.models import ConditionSet, Medium
from yeastphenome.apps.datasets.models import Datatype, Gene, Tag, Collection
from yeastphenome.apps.papers.models import Paper

# Search functions


def get_search_tags():
    """Return a list of tags, each with a name and icon, to return to the
    paper explorer tag search
    """
    queryset = Paper.objects.exclude(
        Q(data_statuses__name__exact="not relevant")
        | Q(tested_statuses__name__exact="not relevant")
    )

    # First and last authors both searched as "authors" - exclude not relevant datasets
    authors = [
        {"value": x[0].lower(), "icon": "👱️", "code": "authors"}
        for x in queryset.exclude(first_author=None)
        .values_list("first_author")
        .distinct()
    ] + [
        {"value": x[0].lower(), "icon": "👱️", "code": "authors"}
        for x in queryset.exclude(last_author=None)
        .values_list("last_author")
        .distinct()
    ]

    # Years
    years = [
        {"value": x[0], "icon": "🕰️", "code": "year"}
        for x in queryset.values_list("pub_date").distinct()
    ]

    # DataTypes
    datatypes = [
        {"value": x[0], "icon": "💽", "code": "datatype"}
        for x in Datatype.objects.values_list("name").distinct()
    ]

    # Collections
    collections = [
        {"value": x[0], "icon": "🏺", "code": "collection"}
        for x in Collection.objects.values_list("name").distinct()
    ]

    # Tags (from dataset)
    tags = [
        {"value": x[0], "icon": "🏷️", "code": "tag"}
        for x in Tag.objects.values_list("name").distinct()
    ]

    # Genes
    genes = [
        {"value": x[0], "icon": "🧬", "code": "gene"}
        for x in Gene.objects.values_list("systematic_name").distinct()
    ]

    # Phenotypes (from dataset)
    phenotypes = [
        {"value": x[0], "icon": "🐶", "code": "phenotype"}
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

    return (
        authors
        + years
        + datatypes
        + tags
        + genes
        + collections
        + mediums
        + phenotypes
        + conditions
    )


def run_search_tag_query(query=None, taglist=None):
    """this function is called from the common/views.py for the explorer function
    It takes in a list of tags (and associated models) to build a query. E.g.:
    [{'value': 'human protein', 'icon': '🏷️', 'code': 'tag', 'style': '--tag-bg:hsl(108,45%,65%)'},
     {'value': 'hap a/hap alpha/hom', 'icon': '🏺', 'code': 'collection', 'style': '--tag-bg:hsl(267,63%,69%)'},
     {'value': 'haploid MatA', 'icon': '🏺', 'code': 'collection', 'style': '--tag-bg:hsl(24,51%,69%)'}]
    The function here must know how to map the code (e.g., Collection) to a model to search
    """
    queries = [] if not query else [query]
    tags = {}
    for tag in taglist or []:
        if tag["code"] in ["", "query"]:
            queries.append(tag["value"])
        else:
            if tag["code"] not in tags:
                tags[tag["code"]] = []
            tags[tag["code"]].append(tag["value"])

    # Exclude the papers marked as "not relevant"
    queryset = Paper.objects.exclude(
        Q(data_statuses__name__exact="not relevant")
        | Q(tested_statuses__name__exact="not relevant")
    )

    # Prepare querysets
    authors_query = Q()
    years_query = Q()
    tag_query = Q()
    gene_query = Q()
    collection_query = Q()
    datatype_query = Q()
    medium_query = Q()
    phenotype_query = Q()
    conditionset_query = Q()

    if "authors" in tags:
        authors_query = Q(
            first_author__iregex="(" + "$|^".join(tags["authors"]) + ")"
        ) | Q(last_author__iregex="(" + "$|^".join(tags["authors"]) + ")")

    if "year" in tags:
        years_query = Q(pub_date__in=tags["year"])

    if "tag" in tags:
        tag_query = Q(dataset__tags__name__iregex="(" + "$|^".join(tags["tag"]) + ")")

    if "gene" in tags:
        gene_query = Q(dataset__data__gene__systematic_name__in=tags["gene"])

    if "collection" in tags:
        collection_query = Q(dataset__collection__name__in=tags["collection"])

    # Only query for data available, data_published / data_measured not useful
    if "datatype" in tags:
        datatype_query = Q(dataset__data_available__name__in=tags["datatype"])

    if "medium" in tags:
        medium_query = Q(dataset__medium__display_name__in=tags["medium"])

    if "phenotype" in tags:
        phenotype_query = Q(dataset__phenotype__name__in=tags["phenotype"])

    if "conditionset" in tags:
        conditionset_query = Q(
            dataset__conditionset__systematic_name__in=tags["conditionset"]
        )

    queryset = queryset.filter(
        authors_query,
        years_query,
        gene_query,
        tag_query,
        collection_query,
        datatype_query,
        medium_query,
        phenotype_query,
        conditionset_query,
    )

    # Now filter down results more, search all fields for query if defined
    if queries:
        queries = "(%s)" % "|".join(queries)
        queryset = queryset.filter(
            Q(dataset__name__iregex=queries)
            | Q(dataset__phenotype__name__iregex=queries)
            | Q(dataset__collection__name__iregex=queries)
            | Q(data_abstract__iregex=queries)
            | Q(pmid__iregex=queries)
            | Q(notes__iregex=queries)
            | Q(dataset__medium__systematic_name__iregex=queries)
            | Q(dataset__conditionset__systematic_name__iregex=queries)
        )

    return queryset.distinct()
