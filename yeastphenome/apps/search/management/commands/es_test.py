from django.core.management.base import BaseCommand

from elasticsearch import Elasticsearch
from elasticsearch.helpers import bulk

from yeastphenome.settings import (
    ELASTICSEARCH_CLOUD_ID,
    ELASTICSEARCH_USERNAME,
    ELASTICSEARCH_PASSWORD
)

from yeastphenome.apps.papers.search import generate_bulk_actions as generate_bulk_actions_papers
from yeastphenome.apps.genes.search import generate_bulk_actions as generate_bulk_actions_genes
from yeastphenome.apps.conditions.search import generate_bulk_actions as generate_bulk_actions_conditions
from yeastphenome.apps.phenotypes.search import generate_bulk_actions as generate_bulk_actions_phenotypes
from yeastphenome.apps.datasets.search import generate_bulk_actions as generate_bulk_actions_datasets


class Command(BaseCommand):

    def add_arguments(self, parser):
        parser.add_argument("engine", type=str)

    def handle(self, *args, **options):

        engine = options["engine"]

        generate_bulk_actions = {
            "papers": generate_bulk_actions_papers(),
            "genes": generate_bulk_actions_genes(),
            "conditions": generate_bulk_actions_conditions(),
            "phenotypes": generate_bulk_actions_phenotypes(),
            "datasets": generate_bulk_actions_datasets(),
        }

        es = Elasticsearch(
            cloud_id=ELASTICSEARCH_CLOUD_ID,
            basic_auth=(ELASTICSEARCH_USERNAME, ELASTICSEARCH_PASSWORD)
        )

        success, errors = bulk(es, generate_bulk_actions[engine])
        self.stdout.write(f"Indexed {success} documents.")
        if errors:
            self.stdout.write("Errors:", errors)