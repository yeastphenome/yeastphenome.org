from django.core.management.base import BaseCommand

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


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument("engine", type=str)

    def handle(self, *args, **options):

        engine = options["engine"]

        app_search = AppSearch(
            ELASTICSEARCH_HOST,
            http_auth=ELASTICSEARCH_AUTH,
        )

        if engine == "genes":
            [schema, json] = genes_define_document()
        elif engine == "conditiontypes":
            [schema, json] = conditiontypes_define_document()
        elif engine == "observables":
            [schema, json] = observables_define_document()
        elif engine == "datasets":
            [schema, json] = datasets_define_document()
        elif engine == "papers":
            [schema, json] = papers_define_document()
        else:
            print("Engine unknown.")

        nr_docs = len(json)
        batch_size = 100
        nr_batches = int(np.ceil(nr_docs / batch_size))
        for ix_batch in np.arange(nr_batches):
            ix_start = ix_batch * batch_size
            ix_end = ix_start + batch_size
            batch = json[ix_start:ix_end]

            print("Uploading batch %d of %d (documents %d-%d)" % (ix_batch, nr_batches, ix_start, ix_end))
            app_search.index_documents(engine_name=engine, documents=batch)

        resp = app_search.put_schema(engine_name=engine, schema=schema)

        self.stdout.write("%s" % resp)
