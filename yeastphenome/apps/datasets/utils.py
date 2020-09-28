from wsgiref.util import FileWrapper
from django.http import StreamingHttpResponse

import requests
import os

SGD_BASE_URL = "https://www.yeastgenome.org/webservice"


def send_file(exported_file, chunk_size=8192):
    """Send file is shared by similarity and dataset downloads, and streams a chunked response to
    the server, the expected octet stream
    """
    response = StreamingHttpResponse(
        FileWrapper(open(exported_file, "rb"), chunk_size),
        content_type="application/octet-stream",
    )
    response["Content-Length"] = os.path.getsize(exported_file)
    response["Content-Disposition"] = "attachment; filename=%s" % os.path.basename(
        exported_file
    )
    return response


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
