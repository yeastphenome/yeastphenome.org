from django.core.management.base import BaseCommand
import sys
import os

from yeastphenome.apps.datasets.models import GeneSimilarity, Gene

# python manage.py import_gene_similarities yp_rows_store.h5

try:
    import pandas
except:
    sys.exit("pandas is required to load the DataFrames from the HD5 files.")


def load_h5(file_path, verbose=True):

    output = {}

    with pandas.HDFStore(file_path) as store:
        ks = store.keys()

    for k in ks:
        k = k.lstrip("\/")
        if verbose:
            print(k)
        output[k] = pandas.read_hdf(file_path, k)

    return output


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument("hdf_file", type=str)

    def handle(self, *args, **options):

        file_path = options.get("hdf_file")
        if file_path in ["", None] or not os.path.exists(file_path):
            sys.exit(f"{file_path} does not exist or is not provided.")

        # Load in the data
        data = load_h5(file_path, verbose=True)

        total = Gene.objects.count()
        for i, name1 in enumerate(data["cosine"].index.tolist()):

            print(f"Parsing gene {i} of {total}...")
            gene1, _ = Gene.objects.get_or_create(systematic_name=name1)
            for name2 in data["cosine"].index.tolist():
                gene2, _ = Gene.objects.get_or_create(systematic_name=name2)

                # Skip null values
                if str(data["cosine"].loc[name1, name2]) == "nan":
                    continue

                # Grab the pvalue and score
                score = float(data["cosine"].loc[name1, name2])
                pvalue = float(data["pvals"].loc[name1, name2])

                # We only want to save diagonal, try both ways
                created = False
                try:
                    sim = GeneSimilarity.objects.get(gene1=gene1, gene2=gene2)
                except:
                    try:
                        sim = GeneSimilarity.objects.get(gene2=gene1, gene1=gene2)
                    except:
                        sim, created = GeneSimilarity.objects.get_or_create(
                            gene1=gene1,
                            gene2=gene2,
                            score=score,
                            metric="cosine",
                            pvalue=pvalue,
                        )

        print("Finished!")
