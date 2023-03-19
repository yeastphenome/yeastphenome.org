from django.core.management.base import BaseCommand

from yeastphenome.apps.datasets.models import Dataset


class Command(BaseCommand):
    def handle(self, *args, **options):

        # super(Command, self).handle(*args, **options)

        all_datasets = Dataset.objects.all_loaded()
        all_datasets = all_datasets.select_related('paper', 'paper__latest_tested_status__status')

        for dataset in all_datasets:

            column1 = dataset.id
            column2 = dataset.name
            column3 = dataset.paper.pmid
            column4 = dataset.paper.latest_tested_status.status.name

            self.stdout.write("%d\t%s\t%d\t%s" % (column1, column2, column3, column4))
