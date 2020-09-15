from django.db.models import Q

from yeastphenome.apps.phenotypes.models import Phenotype, Observable, Tag, Measurement

from yeastphenome.apps.datasets.models import Datatype

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
        {"value": x[0], "icon": "🏷️", "code": "tag"}
        for x in Tag.objects.values_list("name").distinct()
    ]

    # Measurements
    measurements = [
        {"value": x[0], "icon": "🌡️", "code": "measurement"}
        for x in Measurement.objects.values_list("name").distinct()
    ]

    return observables + phenotypes + tags + measurements


def run_search_tag_query(query, taglist=None, return_instances=False):
    """take a query string and a taglist to run the phenotypes query."""
    tags = {}
    for tag in taglist or []:
        if tag["code"] not in tags:
            tags[tag["code"]] = []
        tags[tag["code"]].append(tag["value"])

    # A phenotype search actually returns observables
    queryset = Observable.objects.all()

    # Prepare querysets
    observables_query = Q()
    phenotype_query = Q()
    measurement_query = Q()
    tag_query = Q()

    if "observable" in tags:
        observables_query = Q(name__in=tags["observable"])

    if "tag" in tags:
        tag_query = Q(tags__name__iregex="(" + "$|^".join(tags["tag"]) + ")")

    if "phenotype" in tags:
        phenotype_query = Q(phenotype__name__in=tags["phenotype"])

    if "measurement" in tags:
        measurement_query = Q(phenotype__measurement__name__in=tags["measurement"])

    results = queryset.filter(
        observables_query,
        tag_query,
        phenotype_query,
        measurement_query,
    )

    # Now filter down results more, search all fields for query if defined
    if query not in ["", None]:
        results = results.filter(
            Q(name__icontains=query)
            | Q(tags__name__icontains=query)
            | Q(phenotype__name__icontains=query)
            | Q(phenotype__description__icontains=query)
            | Q(phenotype__measurement__name__icontains=query)
            | Q(phenotype__reporter__icontains=query)
        ).distinct()

    if return_instances:
        return results

    values_list = []
    for observable in results:
        condition_types = ", ".join([x.name for x in observable.conditiontypes()[:7]])
        papers = ", ".join([str(x) for x in observable.papers()[:7]])
        values_list.append([observable.link_detail(), condition_types, papers])

    return {
        "results": values_list,
        "count": len(values_list),
        "datatypes": {x[0]: x[1] for x in Datatype.objects.values_list("id", "name")},
    }
