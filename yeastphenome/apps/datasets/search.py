from yeastphenome.apps.datasets.models import Dataset


def define_document():

    # "id" included by default
    schema = {
        "paper": "text",
        "collection": "text",
        "data_available": "text",
        "medium": "text",
        "conditionset": "text",
        "conditionset_aliases_list_as_str": "text",
        "phenotype": "text",
        "phenotype_aliases_list_as_str": "text",
        "tags_list_as_str": "text",
    }

    datasets = Dataset.objects.all_valid_as_df()
    datasets_json = datasets.to_dict(orient="records")

    return schema, datasets_json
