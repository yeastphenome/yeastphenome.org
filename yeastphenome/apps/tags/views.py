from django.shortcuts import render, reverse, get_object_or_404
from django.db.models import F, Q

from yeastphenome.apps.tags.models import Tag
from yeastphenome.apps.phenotypes.models import Observable, Phenotype


def tag_detail(request, tag_id):

    tag = get_object_or_404(Tag, pk=tag_id)
    observables = Observable.objects.filter(Q(tags=tag) | Q(phenotype__tags=tag)).values()

    context = {
        "tag": tag,
        "phenotypes": observables,
    }

    return render(request, "tags/detail_min.html", context)