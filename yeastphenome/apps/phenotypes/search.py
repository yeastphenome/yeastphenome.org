from yeastphenome.apps.phenotypes.models import Observable

from tqdm import tqdm


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

    observables = Observable.objects.all_valid()

    print("Preparing JSON file for upload...")

    observables_json = []
    for observable in tqdm(observables):

        json = observable.data_indexing()
        observables_json.append(json)

    return schema, observables_json
