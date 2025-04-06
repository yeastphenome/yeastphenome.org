from django.core.management.base import BaseCommand

from yeastphenome.apps.papers.models import Paper

from yeastphenome.apps.papers.utils import (
    get_pubmed_paper_context,
    get_pubmed_paper,
)

from tqdm import tqdm


class Command(BaseCommand):
    def handle(self, *args, **options):

        # super(Command, self).handle(*args, **options)

        papers_queryset = Paper.objects.all()

        for paper in tqdm(papers_queryset):
            try:
                if paper.pmid != 0:
                    xml_data = get_pubmed_paper(paper.pmid)
                    context = get_pubmed_paper_context(paper.pmid, xml_data)
                    paper.title = context['title']
                    paper.authors = ', '.join(context['authors'])
                    paper.abstract = context['abstract']
                    paper.citation = context['citation']
                    paper.save()
            except:
                self.stdout.write("Paper %d couldn't be saved." % paper.id)
                pass

        self.stdout.write("Finished.")
