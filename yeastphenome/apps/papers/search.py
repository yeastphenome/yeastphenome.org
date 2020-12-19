from django.db.models import Q

# from yeastphenome.apps.papers.models import Paper
from yeastphenome.apps.phenotypes.models import Phenotype
from yeastphenome.apps.conditions.models import ConditionType
from yeastphenome.apps.datasets.models import Datatype, Tag, Collection
from yeastphenome.apps.papers.models import Paper

from yeastphenome.apps.common.utils import escape_regex

import itertools


def get_search_tags():
    """Return a list of tags, each with a name and icon, to return to the
    paper explorer tag search
    """
    queryset = Paper.all_valid()

    tags = set(
        itertools.chain(
            queryset.values_list("first_author", flat=True),
            queryset.values_list("last_author", flat=True),
            queryset.values_list("pub_date", flat=True),
            Datatype.objects.values_list("name", flat=True),
            Collection.objects.values_list("name", flat=True),
            Tag.objects.values_list("name", flat=True),
            Phenotype.objects.values_list("name", flat=True),
            ConditionType.objects.values_list("name", flat=True),
            ConditionType.objects.values_list("chebi_name", flat=True),
            ConditionType.objects.values_list("pubchem_name", flat=True),
        )
    )

    # Remove empty values and sort in alphabetical order
    # (key=str necessary to tranform the numeric pub_date to str before comparing to all other strings)
    tags.discard(None)
    tags = sorted(tags, key=str)

    return [{"value": x, "icon": "🧫", "code": "query"} for x in tags if x]


def run_search_tag_query(queries):
    """this function is called from the common/views.py for the explorer function"""
    queries = queries or []

    # Exclude the papers marked as "not relevant," etc.
    queryset = Paper.all_valid()

    # Now filter down results more, search all fields for query if defined
    for query in queries:
        query = escape_regex(query)
        queryset = queryset.filter(
            Q(first_author__iregex=query)
            | Q(last_author__iregex=query)
            | Q(dataset__name__iregex=query)
            | Q(dataset__phenotype__name__iregex=query)
            | Q(dataset__collection__name__iregex=query)
            | Q(data_abstract__iregex=query)
            | Q(pmid__iregex=query)
            | Q(notes__iregex=query)
            | Q(dataset__medium__systematic_name__iregex=query)
            | Q(dataset__conditionset__systematic_name__iregex=query)
        )

    return queryset.distinct()
