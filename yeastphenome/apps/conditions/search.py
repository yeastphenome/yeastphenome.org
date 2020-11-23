from django.db.models import Q, Count

from yeastphenome.apps.conditions.models import ConditionType, Tag


def get_conditiontypes():
    """Shared function to return a list of conditiontypes with a valid paper and
    at least one dataset. We order by the number of datasets.
    """
    return (
        ConditionType.objects.annotate(
            number_of_datasets=Count(
                "condition__conditionset__dataset",
                filter=~Q(
                    condition__conditionset__dataset__paper__latest_data_status__status__name="not relevant"
                ),
            )
        )
        .annotate(
            number_of_papers=Count(
                "condition__conditionset__dataset__paper", distinct=True
            )
        )
        .filter(number_of_datasets__gte=1)
        .order_by("-number_of_datasets")
    )


# Search functions


def get_search_tags():
    """Return a list of tags, each with a name and icon, to return to the
    conditions explorer tag search
    """
    queryset = get_conditiontypes()
    seen = set()

    # Names have duplicates
    def not_seen(value):
        if value in seen:
            return False
        seen.add(value)
        return True

    # Tags
    tags = [
        {"value": x, "icon": "🏷️", "code": "tags"}
        for x in Tag.objects.values_list("name", flat=True).distinct()
        if x not in [None, ""] and not_seen(x)
    ]

    # Any kind of name
    chebi_names = [
        {"value": x, "icon": "📛", "code": "chebi_name"}
        for x in queryset.values_list("chebi_name", flat=True).distinct()
        if x not in [None, ""] and not_seen(x)
    ]

    pubchem_names = [
        {"value": x, "icon": "📛", "code": "pubchem_name"}
        for x in queryset.values_list("pubchem_name", flat=True).distinct()
        if x not in [None, ""] and not_seen(x)
    ]

    other_names = [
        {"value": x, "icon": "📛", "code": "other_name"}
        for x in queryset.values_list("other_names", flat=True).distinct()
        if x not in [None, ""] and not_seen(x)
    ]

    names = [
        {"value": x, "icon": "📛", "code": "name"}
        for x in queryset.values_list("name", flat=True).distinct()
        if x not in [None, ""] and not_seen(x)
    ]

    return tags + chebi_names + other_names + names + pubchem_names


def run_search_tag_query(query, taglist=None):
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

    # We want to search through condition types that have a valid paper and > 0 datasets
    queryset = get_conditiontypes()

    # Filter querysets
    all_queries = Q()

    if "name" in tags:
        for tag in tags["name"]:
            all_queries = all_queries & Q(name__iregex=tag)

    if "chebi_name" in tags:
        for tag in tags["chebi_name"]:
            all_queries = all_queries & Q(chebi_name__iregex=tag)

    if "other_name" in tags:
        for tag in tags["other_name"]:
            all_queries = all_queries & Q(other_name__iregex=tag)

    if "pubchem_name" in tags:
        for tag in tags["pubchem_name"]:
            all_queries = all_queries & Q(pubchem_name__iregex=tag)

    queryset = queryset.filter(all_queries)

    # Now filter down results more, search all fields for query if defined
    if queries:
        queries = "(%s)" % "|".join(queries)
        f = (
            Q(name__iregex=queries)
            | Q(tags__name__iregex=queries)
            | Q(description__iregex=queries)
            | Q(other_names__iregex=queries)
            | Q(pubchem_name__iregex=queries)
            | Q(chebi_name__iregex=queries)
        )

        queryset = queryset.filter(f).distinct()

    # Tags requires a filter each time to work - the AND assumes the same tag name
    # has all names (not what we want)
    if "tags" in tags:
        for tag in tags["tags"]:
            queryset = queryset.filter(tags__name__iregex=tag)

    # Return the queryset
    return queryset
