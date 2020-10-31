from django.core.management.base import BaseCommand
import sys
import os
import tempfile
import time

from yeastphenome.apps.datasets.models import Dataset
from contextlib import closing
import csv
from io import StringIO

from django.db import connection

# if you need to write the import temporary file, then the h5 file is required:
#     python manage.py import_dataset_similarities yp_cols_store.h5

# if you have the export, then it's not
#     python manage.py import_dataset_similarities datasim-export.tsv

# If the file is very big and the database connection cuts, you likely want to use split
# split -l 20000000 datasim-export.tsv datasim-export-partial
# in the latter, be careful about the sep (separator) variable, as it needs to be \t

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


def write_import_file(file_path):

    # Load in the data
    data = load_h5(file_path, verbose=True)

    # Create stream (to write names)
    stream = StringIO()
    writer = csv.writer(stream, delimiter="\t")

    print("Writing to file...")
    total = data["cosine"].shape[0]
    start_write = time.time()
    _, tmpfile = tempfile.mkstemp()

    with open(tmpfile, "w") as csv_file:
        writer = csv.writer(csv_file, delimiter="\t")
        for i, name1 in enumerate(data["cosine"].index.tolist()):
            print(f"Parsing dataset {i} of {total}...")

            # Allow for different versions of database (with genes we don't have
            try:
                dataset1 = Dataset.objects.get(id=name1)
            except Dataset.DoesNotExist:
                continue

            for name2 in data["cosine"].index.tolist():

                # Allow for different versions of database (with genes we don't have)
                try:
                    dataset2 = Dataset.objects.get(id=name2)
                except Dataset.DoesNotExist:
                    continue

                # Only process when in sorted order (skip if not)
                if dataset1.id > dataset2.id or dataset1 == dataset2:
                    continue

                # Skip null values
                if str(data["cosine"].loc[name1, name2]) == "nan":
                    continue

                # Grab the pvalue and score
                score = float(data["cosine"].loc[name1, name2])
                pvalue = float(data["pvals"].loc[name1, name2])

                # Grab the pvalue and score
                writer.writerow([dataset1.id, dataset2.id, score, pvalue])
                writer.writerow([dataset2.id, dataset1.id, score, pvalue])

    end_write = time.time()
    time_write = end_write - start_write
    print(f"Took {time_write} to write similarites to file.")
    return tmpfile


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument("file_path", type=str)

    def handle(self, *args, **options):

        file_path = options.get("file_path")
        if file_path in ["", None] or not os.path.exists(file_path):
            sys.exit(f"{file_path} does not exist or is not provided.")

        sep = "," if file_path.endswith(".csv") else "\t"

        # We need to generate .tsv file
        if file_path.endswith(".h5"):
            print(f"Import file not provided, will generate from {file_path}")
            file_path = write_import_file(file_path)
            sep = "\t"

        # In case we need to generate a file with filtered ids
        # You will still need to split this into pieces aa..af and import each
        # ids = list(Dataset.objects.values_list('id', flat=True))
        # output_file = "dataset-sims-filtered.tsv"
        # with open(output_file, "w") as out:
        #    with open(file_path, "r") as stream:
        #        line = stream.readline()
        #        while line:
        #            columns = [int(x) for x in line.split('\t')[0:2]]
        #            if not any(x for x in columns if x not in ids):
        #                out.write(line)
        #            line = stream.readline()

        import IPython

        IPython.embed()

        # aa,
        print("Creating similarties...")
        create_start = time.time()
        with open(file_path, "r") as stream:
            with closing(connection.cursor()) as cursor:
                cursor.copy_from(
                    file=stream,
                    table="datasets_datasetsimilarity",
                    sep=sep,
                    columns=("dataset1_id", "dataset2_id", "score", "pvalue"),
                )

        create_end = time.time()
        create_time = create_end - create_start
        print(f"Finished! Total time {create_time} seconds.")
