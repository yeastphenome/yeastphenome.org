from yeastphenome.apps.papers.models import Paper


def define_document():

    schema = {
        "systematic_name": "text",
        "pmid": "number",
        "pub_date": "number",
        "data_abstract": "text",
        "conditiontypes_summary": "text",
        "observables_summary": "text",
        "tags_list_as_str": "text",
    }

    papers_df = Paper.objects.all_valid_as_df()
    papers_json = papers_df.to_dict(orient="records")

    return schema, papers_json
