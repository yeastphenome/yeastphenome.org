from yeastphenome.apps.genes.models import Gene


index_name = "index_genes"


schema = {
    "systematic_name": "text",
    "common_name": "text",
    "aliases_list_as_str": "text",
    "description": "text",
}


query_fields = [k for k, v in schema.items() if v == "text"]


field_aliases = {
    "systematic_name": "systematic_name",
    "common_name": "common_name",
    "aliases_list_as_str": "aliases_list_as_str",
    "description": "description",
}


result_fields = [
    "id",
    "systematic_name",
    "common_name",
    "aliases_list_as_str",
    "description",
]


def generate_bulk_actions():
    
    genes_df = Gene.objects.all_valid_as_df()
    
    for _, row in genes_df.iterrows():
        gene = row.to_dict()
        yield {
            "_index": "index_genes",
            "_id": gene.get("id"),
            "_source": gene
        }

