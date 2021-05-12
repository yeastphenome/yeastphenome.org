from wsgiref.util import FileWrapper
from django.http import StreamingHttpResponse

import os


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
