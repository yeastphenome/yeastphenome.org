from yeastphenome.apps.conditions.models import ConditionType


index_name = "index_conditions"


schema = {
    "name": "text",
    "aliases_list_as_str": "text",
    "doses_list_as_str": "text",
    "observables_list_as_str": "text",
    "papers_list_as_str": "text",
    "tags_list_as_str": "text",
}


query_fields = [k for k, v in schema.items() if v == "text"]


field_aliases = {
    "name": "name",
    "aliases_list_as_str": "aliases_list_as_str",
    "doses_list_as_str": "doses_list_as_str",
    "observables_list_as_str": "observables_list_as_str",
    "papers_list_as_str": "papers_list_as_str",
    "tags": "tags_list_as_str",
}


result_fields = [
    "id",
    "name",
    "aliases_list_as_str",
    "doses_list_as_str",
    "observables_list_as_str",
    "papers_list_as_str",
    "tags_list_as_str",
]


def generate_bulk_actions():

    conditiontypes_df = ConditionType.objects.all_valid_as_df()

    for _, row in conditiontypes_df.iterrows():
        conditiontype = row.to_dict()
        yield {
            "_index": "index_conditions",
            "_id": conditiontype.get("id"),
            "_source": conditiontype
        }

