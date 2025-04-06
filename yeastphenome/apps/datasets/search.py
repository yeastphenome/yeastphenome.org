from yeastphenome.apps.datasets.models import Dataset


index_name = "index_datasets"


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


query_fields = [k for k, v in schema.items() if v == "text"]


field_aliases = {
    "paper": "paper",
    "collection": "collection",
    "data_available": "data_available",
    "medium": "medium",
    "conditionset": "conditionset",
    "phenotype": "phenotype",
    "tags": "tags_list_as_str",
}


result_fields = [
    "id",
    "paper",
    "collection",
    "data_available",
    "medium",
    "conditionset",
    "conditionset_aliases_list_as_str",
    "phenotype",
    "phenotype_aliases_list_as_str",
    "tags_list_as_str",
]


def generate_bulk_actions():
    """
    Generates bulk actions for indexing Dataset objects into Elasticsearch.
    """
    datasets_df = Dataset.objects.all_valid_as_df()

    for _, row in datasets_df.iterrows():
        dataset = row.to_dict()
        yield {
            "_index": "index_datasets",
            "_id": dataset.get("id"),
            "_source": dataset
        }

