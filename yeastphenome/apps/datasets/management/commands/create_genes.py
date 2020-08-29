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
        for name in genes:
            gene, created = Gene.objects.get_or_create(systematic_name=name)

        print("Created or found {count} genes.".format(count=Gene.objects.count()))
        # Created 11287 genes.

        # Now go through data, get gene, add and save
        print("Updating data... this may take some time!")
        for data in Data.objects.iterator():

            # Don't add an empty gene
            if not data.orf:
                continue

            # If gene already defined, skip
            if data.gene:
                continue

            gene = Gene.objects.get(systematic_name=data.orf)
            data.gene = gene
            data.save()
