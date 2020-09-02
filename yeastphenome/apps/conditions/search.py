from django.db.models import Q, Count

from yeastphenome.apps.conditions.models import ConditionSet, Medium, Tag
from yeastphenome.apps.datasets.models import Datatype

from itertools import chain

# Search functions


def get_querysets():
    """Return two datasets, one for condition sets and one for mediums (that are structured the same)
    """
    g = Count(
        "dataset",
        filter=~Q(dataset__paper__latest_data_status__status__name="not relevant"),
    )
    queryset1 = (
        ConditionSet.objects.all()
        .annotate(num_datasets=g)
        .filter(num_datasets__gte=0)
        .distinct()
    )
    queryset2 = (
        Medium.objects.all()
        .annotate(num_datasets=g)
        .filter(num_datasets__gte=0)
        .distinct()
    )
    return queryset1, queryset2


def get_search_tags():
    """Return a list of tags, each with a name and icon, to return to the
       conditions explorer tag search
    """
    queryset1, queryset2 = get_querysets()

    # Tags
    tags = [
        {"value": x[0], "icon": "🏷️", "code": "tag"}
        for x in Tag.objects.values_list("name").distinct()
    ]

    # Any kind of name
    names = [
        {"value": x[0], "icon": "📛", "code": "chebi_name"}
        for x in queryset1.values_list("conditions__type__chebi_name").distinct()
        if x[0] not in [None, ""]
    ] + [
        {"value": x[0], "icon": "📛", "code": "chebi_name"}
        for x in queryset2.values_list("conditions__type__chebi_name").distinct()
        if x[0] not in [None, ""]
    ]

    return tags + names


def run_search_tag_query(query, taglist=None, return_instances=False):
    """take a query string and a taglist to run the phenotypes query.
    """
    tags = {}
    for tag in taglist or []:
        if tag["code"] not in tags:
            tags[tag["code"]] = []
        tags[tag["code"]].append(tag["value"])

    queryset1, queryset2 = get_querysets()

    # Filter querysets
    tag_query = Q()

    if "tag" in tags:
        tag_query = Q(
            conditions__type__tags__name__iregex="(" + "$|^".join(tags["tag"]) + ")"
        )

    queryset1 = queryset1.filter(tag_query)
    queryset2 = queryset2.filter(tag_query)

    # Now filter down results more, search all fields for query if defined
    if query not in ["", None]:
        f = (
            Q(systematic_name__icontains=query)
            | Q(common_name__icontains=query)
            | Q(description__icontains=query)
            | Q(display_name__icontains=query)
            | Q(conditions__type__name__icontains=query)
            | Q(conditions__type__other_names__icontains=query)
            | Q(conditions__type__chebi_name__icontains=query)
            | Q(conditions__type__pubchem_name__icontains=query)
        )

        queryset1 = queryset1.filter(f).distinct()
        queryset2 = queryset2.filter(f).distinct()

    # Combine the queryset into a chained list
    if return_instances:
        return list(chain(queryset1, queryset2))

    queryset1_ids = queryset1.values_list("id", flat=True).distinct()
    queryset2_ids = queryset2.values_list("id", flat=True).distinct()

    # NOTE: The original table format called for getting conditions type names nad papers, which explodes the
    # size of the table. This is edited to only return unique ids
    # queryset1 = queryset1.filter(id__in=queryset1_ids).values_list("id", "conditions__type__name", "dataset__paper__id", "dataset__paper__first_author", "dataset__phenotype__name").distinct()
    # queryset2 = queryset2.filter(id__in=queryset2_ids).values_list("id", "conditions__type__name", "dataset__paper__id", "dataset__paper__first_author", "dataset__phenotype__name").distinct()

    # queryset1 = queryset1.filter(id__in=queryset1_ids).values_list("id", "conditions__conditionset__display_name").distinct()
    # queryset2 = queryset2.filter(id__in=queryset2_ids).values_list("id", "conditions__conditionset__display_name").distinct()

    queryset1 = (
        queryset1.filter(id__in=queryset1_ids)
        .values_list("id", "conditions__type__name")
        .distinct()
    )
    queryset2 = (
        queryset2.filter(id__in=queryset2_ids)
        .values_list("id", "conditions__type__name")
        .distinct()
    )

    values_list = list(chain(queryset1, queryset2))
    return {
        "results": values_list,
        "count": len(values_list),
        "datatypes": {x[0]: x[1] for x in Datatype.objects.values_list("id", "name")},
    }
