from django.core.management.base import BaseCommand

from yeastphenome.apps.papers.models import Paper

from tqdm import tqdm


class Command(BaseCommand):
    def handle(self, *args, **options):

        # super(Command, self).handle(*args, **options)

        papers_queryset = Paper.objects.all()

        for paper in tqdm(papers_queryset):
            try:
                paper.save()
            except:
                self.stdout.write("Paper %d couldn't be saved." % paper.id)
                pass

        self.stdout.write("Finished.")
