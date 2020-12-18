from django.db.models import Q

from yeastphenome.apps.phenotypes.models import Phenotype, Observable, Tag, Measurement
from yeastphenome.apps.common.utils import escape_regex

import itertools


def get_search_tags():
    """Return a list of tags, each with a name and icon, to return to the
    phenotype explorer tag search
    """
    tags = set(
        itertools.chain(
            Observable.objects.values_list("name", flat=True),
            Phenotype.objects.values_list("name", flat=True),
            Tag.objects.values_list("name", flat=True),
            Measurement.objects.values_list("name", flat=True),
        )
    )

    # Remove empty values and sort in alphabetical order
    tags.discard(None)
    tags = sorted(tags)

    return [{"value": x, "icon": "🌡️", "code": "query"} for x in tags if x]


def run_search_tag_query(queries):
    """take a query string and a taglist to run the phenotypes query."""
    queries = queries or []

    # A phenotype search actually returns observables
    queryset = Observable.all_valid()

    for query in queries:
        query = escape_regex(query)
        f = (
            Q(name__iregex=query)
            | Q(tags__name__iregex=query)
            | Q(phenotype__name__iregex=query)
            # | Q(phenotype__description__iregex=query)
            # | Q(phenotype__measurement__name__iregex=query)
            | Q(phenotype__reporter__iregex=query)
        )
        queryset = queryset.filter(f)

    return queryset.distinct().order_by("name")
