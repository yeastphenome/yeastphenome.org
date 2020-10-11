from django.db.models import Q

from yeastphenome.apps.conditions.models import ConditionType, Tag

# Search functions


def get_search_tags():
    """Return a list of tags, each with a name and icon, to return to the
    conditions explorer tag search
    """
    queryset = ConditionType.objects.all()

    # Tags
    tags = [
        {"value": x[0], "icon": "🏷️", "code": "tag"}
        for x in Tag.objects.values_list("name").distinct()
    ]

    # Any kind of name
    chebi_names = [
        {"value": x[0], "icon": "📛", "code": "chebi_name"}
        for x in queryset.values_list("chebi_name").distinct()
        if x[0] not in [None, ""]
    ]

    pubchem_names = [
        {"value": x[0], "icon": "📛", "code": "pubchem_name"}
        for x in queryset.values_list("pubchem_name").distinct()
        if x[0] not in [None, ""]
    ]

    other_names = [
        {"value": x[0], "icon": "📛", "code": "other_name"}
        for x in queryset.values_list("other_names").distinct()
        if x[0] not in [None, ""]
    ]

    names = [
        {"value": x[0], "icon": "📛", "code": "name"}
        for x in queryset.values_list("name").distinct()
        if x[0] not in [None, ""]
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

    # We want to search through condition types
    queryset = ConditionType.objects.all()

    # Filter querysets
    tag_query = Q()
    name_query = Q()
    chebi_query = Q()
    other_name_query = Q()
    pubchem_name_query = Q()

    if "tag" in tags:
        tag_query = Q(tags__name__iregex="(" + "$|^".join(tags["tag"]) + ")")

    if "name" in tags:
        name_query = Q(name__iregex="(" + "$|^".join(tags["name"]) + ")")

    if "chebi_name" in tags:
        chebi_query = Q(chebi_name__iregex="(" + "$|^".join(tags["chebi_name"]) + ")")

    if "other_name" in tags:
        other_name_query = Q(
            other_names__iregex="(" + "$|^".join(tags["other_name"]) + ")"
        )

    if "pubchem_name" in tags:
        pubchem_name_query = Q(
            pubchem_name__iregex="(" + "$|^".join(tags["pubchem_name"]) + ")"
        )

    print(tags)
    queryset = queryset.filter(
        tag_query, name_query, chebi_query, other_name_query, pubchem_name_query
    )

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

    # Return the queryset
    return queryset
