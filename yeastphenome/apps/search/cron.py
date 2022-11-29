from django.http import HttpResponse, HttpResponseForbidden
from django.views.decorators.csrf import csrf_exempt

from elastic_enterprise_search import AppSearch

from yeastphenome.apps.genes.search import define_document as genes_define_document
from yeastphenome.apps.conditions.search import (
    define_document as conditiontypes_define_document,
)
from yeastphenome.apps.phenotypes.search import (
    define_document as observables_define_document,
)
from yeastphenome.apps.datasets.search import (
    define_document as datasets_define_document,
)
from yeastphenome.apps.papers.search import define_document as papers_define_document
from yeastphenome.settings import ELASTICSEARCH_HOST, ELASTICSEARCH_AUTH

import numpy as np


@csrf_exempt
def update(request, engine=""):

    response = HttpResponseForbidden()

    # If the request come from the AppEngine cron service
    if "HTTP_USER_AGENT" in request.META:

        if "Google-Cloud-Scheduler" in request.META["HTTP_USER_AGENT"]:
        # if "Safari" in request.META["HTTP_USER_AGENT"]:

            if engine == "":
                # genes not included because doesn't involve updating related indices
                engines = ["conditiontypes", "observables", "datasets", "papers"]
            else:
                engines = [engine]

            for engine in engines:

                if engine == "genes":
                    [schema, json] = genes_define_document()
                elif engine == "conditiontypes":
                    [schema, json] = conditiontypes_define_document()
                elif engine == "observables":
                    [schema, json] = observables_define_document()
                elif engine == "datasets":
                    [schema, json] = datasets_define_document()
                else:
                    [schema, json] = papers_define_document()

                app_search = AppSearch(
                    ELASTICSEARCH_HOST,
                    http_auth=ELASTICSEARCH_AUTH,
                )

                nr_docs = len(json)
                batch_size = 100
                nr_batches = int(np.ceil(nr_docs / batch_size))
                for ix_batch in np.arange(nr_batches):
                    print("Uploading batch %d of %d" % (ix_batch, nr_batches))
                    ix_start = (ix_batch - 1) * batch_size
                    ix_end = ix_start + batch_size - 1
                    batch = json[ix_start:ix_end]

                    app_search.index_documents(engine_name=engine, documents=batch)

                _ = app_search.put_schema(engine_name=engine, schema=schema)

                response = HttpResponse("OK", status=200)
        else:
            response = HttpResponse("", status=301)

    return response

