from django.core.management.base import BaseCommand
import json
import sys

try:
    from yeastphenome.apps.datasets.models import Gene
except:
    sys.exit("Please create the datasets.Gene model before running this.")


class Command(BaseCommand):
    def handle(self, *args, **options):

        # Don't include genes that are integer names (artifact of current database)
        genes = {}
        count = 0
        for gene in Gene.objects.all():
            try:
                int(gene.systematic_name)
            except:
                count += 1
                print(f"Parsing gene {gene.systematic_name}: {count}")
                genes[gene.systematic_name] = gene.id

        with open("genes-lookup.json", "w") as fd:
            fd.writelines(json.dumps(genes, indent=4))
        print(f"Wrote {len(genes)} to file.")
