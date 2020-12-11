from django.db.models import Q, Count

from yeastphenome.apps.conditions.models import ConditionType, Tag
from yeastphenome.apps.common.utils import escape_regex
import itertools


def get_tags():
    """Return same set of tags with annotated dataset count based on query below"""
    return (
        Tag.objects.annotate(
            number_of_conditions=Count(
                "condition__conditionset__conditions__type__name",
            )
        )
        .filter(number_of_conditions__gte=1)
        .order_by("-number_of_conditions")
    )


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
    tags = set(
        itertools.chain(
            Tag.objects.values_list("name", flat=True).distinct(),
            queryset.values_list("chebi_name", flat=True).distinct(),
            queryset.values_list("pubchem_name", flat=True).distinct(),
            queryset.values_list("other_names", flat=True).distinct(),
            queryset.values_list("name", flat=True).distinct(),
            queryset.exclude(condition__medium__display_name__isnull=True)
            .distinct()
            .values_list("condition__medium__display_name", flat=True),
        )
    )

    return [{"value": x, "icon": "📛", "code": "query"} for x in tags if x]


def run_search_tag_query(queries):
    """take a query string and a taglist to run the phenotypes query."""
    queries = queries or []

    # We want to search through condition types that have a valid paper and > 0 datasets
    queryset = get_conditiontypes()

    # Now filter down results more, search all fields for query if defined
    for query in queries:
        query = escape_regex(query)
        f = (
            Q(name__iregex=query)
            | Q(tags__name__iregex=query)
            | Q(description__iregex=query)
            | Q(other_names__iregex=query)
            | Q(pubchem_name__iregex=query)
            | Q(chebi_name__iregex=query)
            | Q(condition__medium__display_name__iregex=query)
        )
        queryset = queryset.filter(f).distinct()

    # Return the queryset
    return queryset
