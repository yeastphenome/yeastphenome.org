from yeastphenome.apps.phenotypes.models import Observable


def define_document():

    schema = {
        "name": "text",
        "description": "text",
        "phenotypes_list_as_str": "text",
        "reporters_list_as_str": "text",
        "conditiontypes_list_as_str": "text",
        "papers_list_as_str": "text",
        "tags_list_as_str": "text",
    }

    observables_df = Observable.objects.all_valid_as_df()
    observables_json = observables_df.to_dict(orient="records")

    return schema, observables_json
