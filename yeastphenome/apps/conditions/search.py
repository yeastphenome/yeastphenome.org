from yeastphenome.apps.conditions.models import ConditionType

from tqdm import tqdm


def define_document():

    schema = {
        "name": "text",
        "aliases_list_as_str": "text",
        "doses_list_as_str": "text",
        "observables_list_as_str": "text",
        "papers_list_as_str": "text",
        "tags_list_as_str": "text",
    }

    conditiontypes = ConditionType.objects.all_valid()

    print("Preparing JSON file for upload...")

    conditiontypes_json = []
    for conditiontype in tqdm(conditiontypes):

        json = conditiontype.data_indexing()
        conditiontypes_json.append(json)

    return schema, conditiontypes_json
