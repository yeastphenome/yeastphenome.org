from django.db.models import F
from django.shortcuts import render, get_object_or_404

from yeastphenome.apps.conditions.models import ConditionType

from ratelimit.decorators import ratelimit
from yeastphenome.settings import (
    VIEW_RATE_LIMIT as rl_rate,
    VIEW_RATE_LIMIT_BLOCK as rl_block,
)


@ratelimit(key="ip", rate=rl_rate, block=rl_block)
def conditiontype_detail(request, conditiontype_id):

    conditiontype = get_object_or_404(ConditionType, pk=conditiontype_id)

    datasets = conditiontype.datasets().values(dataset_id=F("id"),
                                               dataset_paper_name=F("paper__systematic_name"),
                                               dataset_phenotype_name=F("phenotype__name"),
                                               dataset_conditionset_name=F("conditionset__display_name"),
                                               dataset_medium_name=F("medium__display_name"),
                                               dataset_collection_name=F("collection__shortname"),
                                               dataset_data_name=F("data_available__name"))
    num_datasets = datasets.count()

    context = {
        "conditiontype": conditiontype,
        "datasets": datasets[:10],
        "num_datasets": num_datasets,
    }

    return render(request, "conditions/detail_min.html", context)


@ratelimit(key="ip", rate=rl_rate, block=rl_block)
def conditiontype_datasets(request, conditiontype_id):

    conditiontype = get_object_or_404(ConditionType, pk=conditiontype_id)

    datasets = conditiontype.datasets().values(dataset_id=F("id"),
                                               dataset_paper_name=F("paper__systematic_name"),
                                               dataset_phenotype_name=F("phenotype__name"),
                                               dataset_conditionset_name=F("conditionset__display_name"),
                                               dataset_medium_name=F("medium__display_name"),
                                               dataset_collection_name=F("collection__shortname"),
                                               dataset_data_name=F("data_available__name"))
    num_datasets = datasets.count()

    context = {
        "conditiontype": conditiontype,
        "datasets": datasets,
        "num_datasets": num_datasets,
    }

    return render(request, "conditions/datasets_min.html", context)

