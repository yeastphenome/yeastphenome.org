from yeastphenome.apps.papers.models import Paper


index_name = "index_papers"


schema = {
    "systematic_name": "text",
    "pmid": "number",
    "pub_date": "number",
    "authors": "text",
    "title": "text",
    "abstract": "text",
    "citation": "text",
    "data_abstract": "text",
    "conditiontypes_summary": "text",
    "observables_summary": "text",
    "tags_list_as_str": "text",
}


query_fields = [k for k,v in schema.items() if v == "text"]


field_aliases = {
    "systematic_name": "systematic_name",
    "pmid": "pmid",
    "publication": "pub_date",
    "authors": "authors",
    "title": "title",
    "abstract": "abstract",
    "citation": "citation",
    "data_abstract": "data_abstract",
    "conditions": "conditiontypes_summary",
    "phenotypes": "observables_summary",
    "tags": "tags_list_as_str",
}


result_fields = [
    "id",
    "systematic_name",
    "title",
    "authors",
    "citation",
    "pmid",
    "pub_date",
    "conditiontypes_summary",
    "observables_summary",
    "tags_list_as_str",
]


def generate_bulk_actions():

    papers_df = Paper.objects.all_valid_as_df()
    
    for _, row in papers_df.iterrows():
        paper = row.to_dict()
        yield {
            "_index": index_name,
            "_id": paper.get("id"),
            "_source": paper
        }

