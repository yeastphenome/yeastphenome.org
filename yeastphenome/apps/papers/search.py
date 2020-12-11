from django.db.models import Q

# from yeastphenome.apps.papers.models import Paper
from yeastphenome.apps.phenotypes.models import Phenotype
from yeastphenome.apps.conditions.models import ConditionSet, Medium
from yeastphenome.apps.datasets.models import Datatype, Gene, Tag, Collection
from yeastphenome.apps.papers.models import Paper

from yeastphenome.apps.common.utils import escape_regex

import itertools


def get_search_tags():
    """Return a list of tags, each with a name and icon, to return to the
    paper explorer tag search
    """

    queryset = Paper.all()

    tags = set(
        itertools.chain(
            queryset.exclude(first_author=None)
            .distinct()
            .values_list("first_author", flat=True),
            queryset.exclude(last_author=None)
            .distinct()
            .values_list("last_author", flat=True),
            queryset.values_list("pub_date", flat=True).distinct(),
            Datatype.objects.values_list("name", flat=True).distinct(),
            Collection.objects.values_list("name", flat=True).distinct(),
            Tag.objects.values_list("name", flat=True).distinct(),
            Gene.objects.values_list("systematic_name", flat=True).distinct(),
            Phenotype.objects.values_list("name", flat=True).distinct(),
            ConditionSet.objects.values_list("systematic_name", flat=True).distinct(),
            Medium.objects.values_list("display_name", flat=True).distinct(),
        )
    )

    return [{"value": x, "icon": "🧫", "code": "query"} for x in tags if x]


def run_search_tag_query(queries):
    """this function is called from the common/views.py for the explorer function"""
    queries = queries or []

    # Exclude the papers marked as "not relevant"
    queryset = Paper.all()

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
