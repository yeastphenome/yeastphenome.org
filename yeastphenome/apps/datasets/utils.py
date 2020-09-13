import requests

SGD_BASE_URL = "https://www.yeastgenome.org/webservice"


def get_gene_metadata(locus_id):
    url = "%s/locus/%s" % (SGD_BASE_URL, locus_id)
    return requests.get(url=url).json()
