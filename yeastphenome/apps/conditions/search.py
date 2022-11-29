from yeastphenome.apps.conditions.models import ConditionType


def define_document():

    # "id" included by default
    schema = {
        "name": "text",
        "aliases_list_as_str": "text",
        "doses_list_as_str": "text",
        "observables_list_as_str": "text",
        "papers_list_as_str": "text",
        "tags_list_as_str": "text",
    }

    conditiontypes = ConditionType.objects.all_valid_as_df()
    conditiontypes_json = conditiontypes.to_dict(orient="records")

    return schema, conditiontypes_json
