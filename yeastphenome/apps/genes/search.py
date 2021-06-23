from django.contrib.postgres.aggregates import StringAgg

from yeastphenome.apps.genes.models import Gene


def define_document():

    schema = {
        "systematic_name": "text",
        "common_name": "text",
        "aliases_list_as_str": "text",
        "description": "text",
    }

    genes = Gene.objects.all_valid()

    agg_field = "aliases__name"
    genes = genes.annotate(
        aliases_list_as_str=StringAgg(
            agg_field, "; ", distinct=True, ordering=agg_field
        )
    )

    genes_vals = list(
        genes.values(
            "id", "systematic_name", "common_name", "aliases_list_as_str", "description"
        )
    )

    return schema, genes_vals
