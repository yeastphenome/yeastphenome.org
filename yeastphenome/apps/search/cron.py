from django.http import HttpResponse, HttpResponseForbidden

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


def update(request):
    # If the request come from the AppEngine cron service
    if "HTTP_X_APPENGINE_CRON" in request.META:

        if request.META["HTTP_X_APPENGINE_CRON"] == "true":

            engines = ["genes", "conditiontypes", "observables", "datasets", "papers"]

            app_search = AppSearch(
                ELASTICSEARCH_HOST,
                http_auth=ELASTICSEARCH_AUTH,
            )

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

                return HttpResponse("", status=200)
    else:
        return HttpResponseForbidden()
