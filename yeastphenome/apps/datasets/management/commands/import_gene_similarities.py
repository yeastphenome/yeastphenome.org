from django.core.management.base import BaseCommand
import sys
import os
import tempfile
import time

from yeastphenome.apps.datasets.models import Gene

from contextlib import closing
import csv
from io import StringIO

from django.db import connection

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

        # Skip diagonals! We know a gene is == to itself!

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
                print(f"Parsing gene {i} of {total}...")

                # Allow for different versions of database (with genes we don't have
                try:
                    gene1 = Gene.objects.get(systematic_name=name1)
                except Gene.DoesNotExist:
                    continue

                for name2 in data["cosine"].index.tolist():

                    # Allow for different versions of database (with genes we don't have)
                    try:
                        gene2 = Gene.objects.get(systematic_name=name2)
                    except Gene.DoesNotExist:
                        continue

                    # Only process when in sorted order (skip if not)
                    if gene1.systematic_name > gene2.systematic_name or gene1 == gene2:
                        continue

                    # Skip null values
                    if str(data["cosine"].loc[name1, name2]) == "nan":
                        continue

                    # Grab the pvalue and score
                    score = float(data["cosine"].loc[name1, name2])
                    pvalue = float(data["pvals"].loc[name1, name2])

                    # Grab the pvalue and score
                    writer.writerow([gene1.id, gene2.id, "cosine", score, pvalue])
                    writer.writerow([gene2.id, gene1.id, "cosine", score, pvalue])

        end_write = time.time()
        time_write = end_write - start_write
        print(f"Took {time_write} to write similarites to file.")
        print("Creating similarties...")
        create_start = time.time()
        with open(tmpfile, "r") as stream:
            with closing(connection.cursor()) as cursor:
                cursor.copy_from(
                    file=stream,
                    table="datasets_genesimilarity",
                    sep="\t",
                    columns=("gene1_id", "gene2_id", "metric", "score", "pvalue"),
                )

        create_end = time.time()
        create_time = create_end - create_start
        print(f"Finished! Total time {create_time} seconds.")
