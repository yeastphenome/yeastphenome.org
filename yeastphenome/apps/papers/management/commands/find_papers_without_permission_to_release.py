from django.core.management.base import BaseCommand

from yeastphenome.apps.papers.models import Paper


class Command(BaseCommand):

    # Output of "ls -d */ > yp_data_datasets.txt
    def add_arguments(self, parser):
        parser.add_argument('path', type=str)

    def handle(self, *args, **options):

        with open(options['path']) as f:
            paper_ids = f.readlines()

        for paper_id in paper_ids:
            paper_id = paper_id.replace("/", "")
            try:
                paper = Paper.objects.filter(pmid__exact=int(paper_id))[0]
                datasets = paper.datasets.all()
                for dataset in datasets:
                    if not dataset.data_source:
                        self.stdout.write('%s' % paper)
                    if dataset.data_source and not dataset.data_source.release:
                        self.stdout.write('%s' % paper)
            except:
                self.stdout.write('%s' % paper_id)
