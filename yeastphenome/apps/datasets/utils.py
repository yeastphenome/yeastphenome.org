from wsgiref.util import FileWrapper
from django.http import StreamingHttpResponse
from yeastphenome.apps.datasets.models import Gene, Data

from datetime import datetime
import requests
import tempfile
import os

SGD_BASE_URL = "https://www.yeastgenome.org/webservice"


def send_file(exported_file, chunk_size=8192):
    """Send file is shared by similarity and dataset downloads, and streams a chunked response to
    the server, the expected octet stream
    """
    response = StreamingHttpResponse(
        FileWrapper(open(exported_file, "rb"), chunk_size),
        content_type="application/octet-stream",
    )
    response["Content-Length"] = os.path.getsize(exported_file)
    response["Content-Disposition"] = "attachment; filename=%s" % os.path.basename(
        exported_file
    )
    return response


def generate_dated_download(prefix="yeastphenome-datasets"):
    """Generate the filename for a download with some prefix and the date"""
    timestamp = datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
    return os.path.join(tempfile.gettempdir(), "%s-%s.txt" % (prefix, timestamp))


def get_gene_metadata(locus_id):
    try:
        url = "%s/locus/%s" % (SGD_BASE_URL, locus_id)
        response = requests.get(url=url).json()
        # Filter down aliases to only include aliases
        response["aliases"] = [
            x for x in response.get("aliases", []) if x["category"] == "Alias"
        ]
        return response
    except:
        return {}


def prepare_dataset_download(datasets):
    """A general function to take a list of datasets, and prepare a data frame
    to download with columns: ORF, dataset1 .. datasetN and rows
    ORF-dataset pair (values).
    """
    import pandas as pd

    # Get all data for the relevant datasets
    data = Data.objects.filter(dataset_id__in=datasets.values("id")).all()

    # Load the data into a pandas dataframe
    df = pd.DataFrame.from_records(data.values())

    # If no datasets, return empty
    if df.empty:
        return df

    # Make sure values are numeric
    df["value"] = df["value"].astype(float)

    # Transform list of gene-dataset-value into a gene x dataset matrix
    df_matrix = pd.pivot_table(
        df, index="gene_id", columns="dataset_id", values="value"
    )

    # Rename gene ids to ORFs
    genes = Gene.objects.all()
    genes_df = pd.DataFrame.from_records(genes.values())
    genes_df.set_index("id", inplace=True)
    df_matrix.index = genes_df.loc[df_matrix.index, "systematic_name"].values

    # Rename dataset ids to dataset names
    datasets_df = pd.DataFrame.from_records(datasets.values())
    datasets_df.set_index("id", inplace=True)
    df_matrix.columns = datasets_df.loc[df_matrix.columns, "name"].values
    return df
