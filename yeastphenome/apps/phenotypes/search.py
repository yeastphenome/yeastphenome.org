from django.db.models import Q

from yeastphenome.apps.phenotypes.models import Phenotype, Observable, Tag, Measurement

# Search functions


def get_search_tags():
    """Return a list of tags, each with a name and icon, to return to the
    phenotype explorer tag search
    """
    # Observables
    observables = [
        {"value": x[0], "icon": "👁️", "code": "observable"}
        for x in Observable.objects.values_list("name").distinct()
    ]

    # Phenotypes
    phenotypes = [
        {"value": x[0], "icon": "🐶", "code": "phenotype"}
        for x in Phenotype.objects.values_list("name").distinct()
    ]

    # Tags
    tags = [
        {"value": x[0], "icon": "🏷️", "code": "tags"}
        for x in Tag.objects.values_list("name").distinct()
    ]

    # Measurements
    measurements = [
        {"value": x[0], "icon": "🌡️", "code": "measurement"}
        for x in Measurement.objects.values_list("name").distinct()
    ]

    return observables + phenotypes + tags + measurements


def run_search_tag_query(query=None, taglist=None):
    """take a query string and a taglist to run the phenotypes query."""
    queries = [] if not query else [query]
    tags = {}
    for tag in taglist or []:
        if tag["code"] in ["", "query"]:
            queries.append(tag["value"])
        else:
            if tag["code"] not in tags:
                tags[tag["code"]] = []
            tags[tag["code"]].append(tag["value"])

    # A phenotype search actually returns observables
    queryset = (
        Observable.objects.exclude(
            phenotype__dataset__paper__latest_data_status__status__name="not relevant"
        )
        .order_by("name")
        .all()
    )

    # Prepare querysets
    all_queries = Q()

    if "observable" in tags:
        for tag in tags["observable"]:
            all_queries = all_queries & Q(name__iregex=tag)

    if "phenotype" in tags:
        for tag in tags["phenotype"]:
            all_queries = all_queries & Q(phenotype__name__iregex=tag)

    if "measurement" in tags:
        for tag in tags["measurement"]:
            all_queries = all_queries & Q(phenotype__measurement__name__iregex=tag)

    queryset = queryset.filter(all_queries)

    if queries:
        queries = "(%s)" % "|".join(queries)
        f = (
            Q(name__icontains=queries)
            | Q(tags__name__iregex=queries)
            | Q(phenotype__name__iregex=queries)
            | Q(phenotype__description__iregex=queries)
            | Q(phenotype__measurement__name__iregex=queries)
            | Q(phenotype__reporter__iregex=queries)
        )
        queryset = queryset.filter(f).distinct()

    if "tags" in tags:
        for tag in tags["tags"]:
            queryset = queryset.filter(tags__name__iregex=tag)

    return queryset
