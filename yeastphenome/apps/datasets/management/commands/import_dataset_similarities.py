from django.core.management.base import BaseCommand
import sys
import os

from yeastphenome.apps.datasets.models import DatasetSimilarity, Dataset

# python manage.py import_dataset_similarities yp_cols_store.h5

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

        total = Dataset.objects.count()
        for i, name1 in enumerate(data["cosine"].index.tolist()):
            if i < 3310:
                continue

            print(f"Parsing dataset {i} of {total}...")

            try:
                dataset1 = Dataset.objects.get(id=name1)
            except Dataset.DoesNotExist:
                continue

            for name2 in data["cosine"].index.tolist():

                try:
                    dataset2 = Dataset.objects.get(id=name2)
                except Dataset.DoesNotExist:
                    continue

                # Skip null values
                if str(data["cosine"].loc[name1, name2]) == "nan":
                    continue

                # Grab the pvalue and score
                score = float(data["cosine"].loc[name1, name2])
                pvalue = float(data["pvals"].loc[name1, name2])

                # We only want to save diagonal, try both ways
                created = False
                try:
                    sim = DatasetSimilarity.objects.get(
                        dataset1=dataset1, dataset2=dataset2
                    )
                except:
                    try:
                        sim = DatasetSimilarity.objects.get(
                            dataset1=dataset2, dataset2=dataset1
                        )
                    except:
                        sim, created = DatasetSimilarity.objects.get_or_create(
                            dataset1=dataset1,
                            dataset2=dataset2,
                            score=score,
                            metric="cosine",
                            pvalue=pvalue,
                        )
        print("Finished!")
