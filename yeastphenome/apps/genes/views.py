from django.shortcuts import render, redirect
from django.shortcuts import get_object_or_404, reverse
from django.http import HttpResponse

from yeastphenome.apps.datasets.models import Data, Dataset
from yeastphenome.apps.genes.models import Gene
from yeastphenome.apps.common.utils_format import update_values_with_percentile

from yeastphenome.settings import DOWNLOAD_PREFIX

import pandas as pd
import numpy as np


def index(request):
    return redirect("search:search")


def detail(request, gene_id):

    gene = get_object_or_404(Gene, pk=gene_id)

    scores = gene.get_scores()
    num_scores = scores.count()
    scores_lowest = update_values_with_percentile(scores.order_by("valuez"), "valuez")[
        :10
    ]
    scores_highest = update_values_with_percentile(
        scores.order_by("-valuez"), "valuez"
    )[:10]

    similarities_lowest = gene.get_similarities_faiss(n=10, ascending=True)
    similarities_highest = gene.get_similarities_faiss(n=10, ascending=False)
    num_similarities = 4554

    context = {
        "gene": gene,
        "num_scores": num_scores,
        "scores_lowest": scores_lowest,
        "scores_highest": scores_highest,
        "num_similarities": num_similarities,
        "similarities_lowest": similarities_lowest,
        "similarities_highest": similarities_highest,
    }

    return render(request, "genes/detail_min.html", context)


def scores(request, gene_id):

    gene = get_object_or_404(Gene, pk=gene_id)
    scores = gene.get_scores().order_by("valuez")
    scores = update_values_with_percentile(scores, "valuez")

    context = {
        "gene": gene,
        "scores": scores,
    }

    return render(request, "genes/scores_min.html", context)


def download_scores(request, gene1_id, gene2_id=None):

    gene1 = get_object_or_404(Gene, pk=gene1_id)
    scores1 = gene1.get_scores().order_by("valuez")
    scores1_df = pd.DataFrame(list(scores1))

    if gene2_id:
        gene2 = get_object_or_404(Gene, pk=gene2_id)
        scores2 = gene2.get_scores().order_by("valuez")
        scores2_df = pd.DataFrame(list(scores2))

        scores_df = scores1_df.merge(scores2_df, how="outer", on="dataset_id", suffixes=('_gene1', '_gene2'))
        scores_df = scores_df[['dataset_id', 'dataset_name_gene1', 'valuez_gene1', 'valuez_gene2']]
        scores_df.columns = ['Screen ID', 'Screen name', 'NPV ' + str(gene1), 'NPV ' + str(gene2)]
        filename = "%s_%s_%s_NPVs.txt" % (DOWNLOAD_PREFIX, gene1.urlencode(), gene2.urlencode())
    else:
        scores_df = scores1_df
        scores_df = scores_df[['dataset_id', 'dataset_name', 'valuez']]
        scores_df.columns = ['Screen ID', 'Screen name', 'NPV ' + str(gene1)]
        filename = "%s_%s_NPVs.txt" % (DOWNLOAD_PREFIX, gene1.urlencode())

    # Prepare the HttpResponse
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="%s"' % filename

    scores_df.to_csv(path_or_buf=response, sep="\t", index=False)

    return response

def similarities(request, gene_id):

    gene = get_object_or_404(Gene, pk=gene_id)
    similarities = gene.get_similarities_faiss(ascending=False)

    context = {
        "gene": gene,
        "similarities": similarities,
    }

    return render(request, "genes/similarities_min.html", context)


def download_similarities(request, gene_id):

    gene = get_object_or_404(Gene, pk=gene_id)
    similarities = gene.get_similarities_faiss(ascending=False)


    similarities_df = pd.DataFrame(list(similarities))
    similarities_df.columns = ['Correlation', 'Percentile',
                               'Gene ID', 'Gene systematic name', 'Gene common name']

    # Prepare the HttpResponse
    filename = "%s_%s_similarities.txt" % (DOWNLOAD_PREFIX, gene.urlencode())
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="%s"' % filename

    similarities_df.to_csv(path_or_buf=response, sep="\t", index=False)

    return response


def scatterplot_gc(request, gene1_id, gene2_id):

    gene1 = get_object_or_404(Gene, pk=gene1_id)
    gene2 = get_object_or_404(Gene, pk=gene2_id)

    gene1_link = reverse("genes:detail", args=[gene1_id])
    gene2_link = reverse("genes:detail", args=[gene2_id])

    similarity = gene1.get_similarity_to_faiss(gene2)

    data = Data.objects.all_valid().filter(gene_id__in=[gene1_id, gene2_id])
    data = data.values("gene_id", "dataset_id", "valuez")

    df = pd.DataFrame(list(data))
    df = df.loc[df["valuez"].notnull()]
    df["valuez"] = pd.to_numeric(df["valuez"])

    df_matrix = pd.pivot_table(
        df, index="dataset_id", columns="gene_id", values="valuez"
    )
    df_matrix = df_matrix.loc[df_matrix.isnull().sum(axis=1) == 0, ]

    # Get dataset names
    datasets = Dataset.objects.all_valid().values("id", "name")
    datasets_df = pd.DataFrame(list(datasets))
    datasets_df.set_index("id", inplace=True)

    df_matrix["dataset_name"] = datasets_df["name"]
    df_matrix["dataset_link"] = df_matrix.apply(
        lambda row: reverse("datasets:detail", args=[row.name]), axis=1
    )
    df_matrix["tooltip"] = df_matrix.apply(
        lambda row: '<div class="alert alert-light" role="alert">'
                    + '<p><strong>Screen:</strong> '
                    + '<a href="' + row["dataset_link"] + '">' + row["dataset_name"] + '</a></p>'
                    + '<p><strong>Normalized phenotypic values (NPVs):</strong>'
                    + '<br><a href="' + gene1_link + '">' + str(gene1) + '</a>: '
                    + '{:.2f}'.format(row[gene1_id])
                    + '<br><a href="' + gene2_link + '">' + str(gene2) + '</a>: '
                    + '{:.2f}'.format(row[gene2_id]) + '</p>'
                    + "</div>", axis=1
    )

    df_matrix.set_index("dataset_name", inplace=True, drop=False)

    min_axis = np.floor(np.nanmin(df_matrix[[gene1_id, gene2_id]].min(axis=0)))
    max_axis = np.ceil(np.nanmax(df_matrix[[gene2_id, gene2_id]].max(axis=0)))

    values = df_matrix[[gene1_id, gene2_id, "tooltip"]].values.tolist()

    context = {
        "gene1": gene1,
        "gene2": gene2,
        "values": values,
        "min_axis": min_axis,
        "max_axis": max_axis,
        "similarity": similarity
    }
    return render(request, "genes/scatterplot_gc.html", context)
