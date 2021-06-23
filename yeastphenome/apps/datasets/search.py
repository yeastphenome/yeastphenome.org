from yeastphenome.apps.datasets.models import Dataset

from tqdm import tqdm


def define_document():

    schema = {
        "paper": "text",
        "collection": "text",
        "data_available": "text",
        "phenotype": "text",
        "conditions": "text",
        "medium": "text",
        "tags_list_as_str": "text",
    }

    datasets = Dataset.objects.all_valid()

    print("Preparing JSON file for upload...")

    datasets_json = []
    for dataset in tqdm(datasets):

        json = dataset.data_indexing()
        datasets_json.append(json)

    return schema, datasets_json
