from django.core.management.base import BaseCommand
import sys

try:
    from yeastphenome.apps.datasets.models import Data, Gene
except:
    sys.exit("Please create the datasets.Gene model before running this.")


class Command(BaseCommand):
    def handle(self, *args, **options):

        print("Creating genes...")
        genes = Data.objects.values_list("orf", flat=True).distinct()

        # Create all genes!
        total = len(genes)

        # Done in groups with update so we don't need to loop through millions
        # of datasets! It will still take some time.
        for i, name in enumerate(genes):
            print(f"Parsing gene {i} of {total}...")
            gene, created = Gene.objects.get_or_create(systematic_name=name)

            # Find all associated Data and update with the correct gene
            Data.objects.filter(orf=gene.systematic_name).update(gene=gene)
