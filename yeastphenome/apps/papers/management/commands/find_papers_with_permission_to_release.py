from django.core.management.base import BaseCommand
from django.db.models import Q

from yeastphenome.apps.papers.models import Paper


class Command(BaseCommand):

    def handle(self, *args, **options):

        papers = Paper.objects.all_loaded()

        for paper in papers:
            self.stdout.write('%s' % paper.pmid)
