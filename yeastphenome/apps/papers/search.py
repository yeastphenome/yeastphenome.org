from yeastphenome.apps.papers.models import Paper

from tqdm import tqdm


def define_document():

    schema = {
        "systematic_name": "text",
        "pmid": "number",
        "pub_date": "number",
        # "observables_list_as_str": "text",
        # "phenotypes_aliases_list_as_str": "text",
        # "conditiontypes_list_as_str": "text",
        # "conditions_aliases_list_as_str": "text",
        "tags_list_as_str": "text"
    }

    papers = Paper.objects.all_valid()

    print("Preparing JSON file for upload...")

    papers_json = []
    for paper in tqdm(papers):

        json = paper.data_indexing()
        papers_json.append(json)

    return schema, papers_json
