import requests

SGD_BASE_URL = "https://www.yeastgenome.org/webservice"


def get_gene_metadata(locus_id):
    try:
        url = "%s/locus/%s" % (SGD_BASE_URL, locus_id)
        response = requests.get(url=url).json()
        # Filter down aliases to only include aliases
        response["aliases"] = [
            x for x in response.get("aliases", []) if x["category"] == "Alias"
        ]
        return response
    except:
        return {}
