from yeastphenome.apps.genes.models import Gene


def define_document():

    schema = {
        "systematic_name": "text",
        "common_name": "text",
        "aliases_list_as_str": "text",
        "description": "text",
    }

    genes = Gene.objects.all_valid_as_df()
    genes_json = genes.to_dict(orient="records")

    return schema, genes_json
