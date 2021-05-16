from django.db.models import Q

from yeastphenome.apps.conditions.models import ConditionType, Tag
from yeastphenome.apps.common.utils import escape_regex
import itertools


# Search functions


def get_search_tags():
    """Return a list of tags, each with a name and icon, to return to the
    conditions explorer tag search
    """
    queryset = ConditionType.objects.all_valid()
    tags = set(
        itertools.chain(
            Tag.objects.values_list("name", flat=True),
            queryset.values_list("chebi_name", flat=True),
            queryset.values_list("pubchem_name", flat=True),
            queryset.values_list("name", flat=True),
        )
    )

    # Remove empty values and sort in alphabetical order
    tags.discard(None)
    tags = sorted(tags)

    return [{"value": x, "icon": "📛", "code": "query"} for x in tags if x]


def run_search_tag_query(queries):
    """take a query string and a taglist to run the phenotypes query."""
    queries = queries or []

    # We want to search through condition types that have a valid paper and > 0 datasets
    queryset = ConditionType.objects.all_valid()

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
