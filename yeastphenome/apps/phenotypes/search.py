from yeastphenome.apps.phenotypes.models import Observable


index_name = "index_phenotypes"


schema = {
        "name": "text",
        "description": "text",
        "phenotypes_list_as_str": "text",
        "reporters_list_as_str": "text",
        "conditiontypes_list_as_str": "text",
        "papers_list_as_str": "text",
        "tags_list_as_str": "text",
    }


query_fields = [k for k, v in schema.items() if v == "text"]


field_aliases = {
    "name": "name",
    "description": "description",
    "phenotypes_list_as_str": "phenotypes_list_as_str",
    "reporters_list_as_str": "reporters_list_as_str",
    "conditiontypes_list_as_str": "conditiontypes_list_as_str",
    "papers_list_as_str": "papers_list_as_str",
    "tags": "tags_list_as_str",
}


result_fields = [
    "id",
    "name",
    "description",
    "phenotypes_list_as_str",
    "reporters_list_as_str",
    "conditiontypes_list_as_str",
    "papers_list_as_str",
    "tags_list_as_str",
]


def generate_bulk_actions():
    """
    Generates bulk actions for indexing Observable objects in Elasticsearch.
    Each Observable object is converted to a dictionary and yielded as a
    bulk action for Elasticsearch indexing.
    """

    observables_df = Observable.objects.all_valid_as_df()

    for _, row in observables_df.iterrows():
        observable = row.to_dict()
        yield {
            "_index": "index_phenotypes",
            "_id": observable.get("id"),
            "_source": observable
        }

