from django.core.management.base import BaseCommand
from django.db.models import Q

from yeastphenome.apps.datasets.models import Dataset


class Command(BaseCommand):
    def handle(self, *args, **options):

        # super(Command, self).handle(*args, **options)

        datasets = Dataset.objects.all()
        datasets = datasets.filter(collection__shortname__in=["het"])

        f = Q(paper__latest_data_status__status__name__exact="loaded") & Q(
            paper__latest_tested_status__status__name__in=[
                "loaded",
                "request abandoned",
                "not available",
            ]
        )
        datasets = datasets.filter(f)

        datasets = datasets.select_related('paper', 'paper__latest_tested_status__status')

        for dataset in datasets:

            column1 = dataset.id
            column2 = dataset.name
            column3 = dataset.paper.pmid
            column4 = dataset.paper.latest_tested_status.status.name
            column5 = dataset.tested_num

            self.stdout.write("%d\t%s\t%d\t%s\t%d" % (column1, column2, column3, column4, column5))
