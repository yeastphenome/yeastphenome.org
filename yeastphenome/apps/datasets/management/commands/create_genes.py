from django.core.management.base import BaseCommand
import sys

from yeastphenome.apps.datasets.utils import get_gene_metadata

try:
    from yeastphenome.apps.datasets.models import Data, Gene, GeneAlias
except:
    sys.exit("Please create the datasets.Gene model before running this.")


class Command(BaseCommand):
    def handle(self, *args, **options):

        print("Creating genes...")
        # genes = Data.objects.values_list("orf", flat=True).distinct()
        # If genes are already created in database, can obtain with this line (much faster)
        genes = list(Gene.objects.values_list("systematic_name", flat=True).distinct())

        # Create all genes!
        total = len(genes)

        # Done in groups with update so we don't need to loop through millions
        # of datasets! It will still take some time.
        for i, name in enumerate(genes):

            # Only create genes that are not integers
            try:
                int(name)
            except:
                print(f"Parsing gene {name}: {i} of {total}...")
                try:
                    meta = get_gene_metadata(name)
                except:
                    print(f"Issue with obtaining gene {name} metadata from SGD.")
                    meta = {}

                # Create gene aliases - we only want ones that are category "Alias"
                alias_names = [
                    x["display_name"]
                    for x in meta.get("aliases", [])
                    if x["category"] == "Alias"
                ]

                # Get display name
                common_name = meta.get("display_name") or meta.get("gene_name")
                sgdid = meta.get("sgdid")

                # Try to create in bulk, unlikely to have repeats (but not likely)
                try:
                    aliases = [GeneAlias(name=x) for x in alias_names]
                    aliases = GeneAlias.objects.bulk_create(aliases)
                except:
                    aliases = []
                    for alias_name in alias_names:
                        alias, _ = GeneAlias.objects.get_or_create(name=alias_name)
                        aliases.append(alias)

                gene, created = Gene.objects.get_or_create(systematic_name=name)
                print(f"sgdid: {sgdid}, primary_sgdid: {gene.primary_sgdid}")
                gene.common_name = common_name

                for alias in aliases:
                    gene.aliases.add(alias)

                # Don't add sgdid if not defined
                if sgdid:
                    gene.primary_sgdid = sgdid
                else:
                    print(f"Warning, sgdid is not defined for {name}")
                gene.save()
                # Find all associated Data and update with the correct gene
                # If genes not yet associated, comment out this line
                # Data.objects.filter(orf=gene.systematic_name).update(gene=gene)
