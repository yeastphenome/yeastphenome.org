from django.shortcuts import render, redirect
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, reverse
from django.conf import settings
from django.views.decorators.cache import never_cache

from yeastphenome.apps.papers.models import Paper
from yeastphenome.apps.datasets.models import (
    Dataset,
    Data,
)
from yeastphenome.apps.genes.models import Gene
from yeastphenome.apps.datasets.utils import send_file
from yeastphenome.apps.conditions.models import ConditionType, Medium
from yeastphenome.apps.phenotypes.models import Observable
from yeastphenome.apps.common.utils_format import update_values_with_percentile

from libchebipy import ChebiEntity
import os
import pandas as pd
import numpy as np
import tempfile

from django_ratelimit.decorators import ratelimit
from yeastphenome.settings import (
    VIEW_RATE_LIMIT as rl_rate,
    VIEW_RATE_LIMIT_BLOCK as rl_block,
    DOWNLOAD_PREFIX
)


@ratelimit(key="ip", rate=rl_rate, block=rl_block)
def index(request):
    return redirect("search:search")


@ratelimit(key="ip", rate=rl_rate, block=rl_block)
def detail(request, dataset_id):

    dataset = get_object_or_404(Dataset, pk=dataset_id)

    data_availability = dataset.get_data_availability()

    scores = dataset.get_scores()
    num_scores = scores.count()
    scores_lowest = update_values_with_percentile(scores.order_by("valuez"), "valuez")[
        :10
    ]
    scores_highest = update_values_with_percentile(
        scores.order_by("-valuez"), "valuez"
    )[:10]

    similarities = dataset.get_similarities()
    num_similarities = similarities.count()
    similarities_lowest = update_values_with_percentile(
        similarities.order_by("score"), "score"
    )[:10]
    similarities_highest = update_values_with_percentile(
        similarities.order_by("-score"), "score"
    )[:10]

    context = {
        "dataset": dataset,
        "data_availability": data_availability,
        "num_scores": num_scores,
        "scores_lowest": scores_lowest,
        "scores_highest": scores_highest,
        "num_similarities": num_similarities,
        "similarities_lowest": similarities_lowest,
        "similarities_highest": similarities_highest,
    }

    return render(request, "datasets/detail_min.html", context)


@ratelimit(key="ip", rate=rl_rate, block=rl_block)
def scatterplot_gc(request, dataset1_id, dataset2_id):

    dataset1 = get_object_or_404(Dataset, pk=dataset1_id)
    dataset2 = get_object_or_404(Dataset, pk=dataset2_id)

    dataset1_link = reverse("datasets:detail", args=[dataset1_id])
    dataset2_link = reverse("datasets:detail", args=[dataset2_id])

    similarity = dataset1.get_similarity_to(dataset2)

    data = Data.objects.filter(dataset_id__in=[dataset1_id, dataset2_id])
    data = data.values("gene_id", "dataset_id", "valuez")

    df = pd.DataFrame(list(data))
    df = df.loc[df["valuez"].notnull()]
    df["valuez"] = pd.to_numeric(df["valuez"])

    df_matrix = pd.pivot_table(
        df, index="gene_id", columns="dataset_id", values="valuez"
    )
    df_matrix = df_matrix.loc[df_matrix.isnull().sum(axis=1) == 0, ]

    # Get gene names
    genes = Gene.objects.all_valid().values("id", "systematic_name", "common_name", "description")
    genes_df = pd.DataFrame(list(genes))
    genes_df["name"] = genes_df["common_name"] + " / " + genes_df["systematic_name"]
    genes_df.set_index("id", inplace=True)

    df_matrix["gene_name"] = genes_df["name"]
    df_matrix["gene_description"] = genes_df["description"]
    df_matrix["gene_link"] = df_matrix.apply(
        lambda row: reverse("genes:detail", args=[row.name]), axis=1
    )
    df_matrix["tooltip"] = df_matrix.apply(
        lambda row: '<div class="alert alert-light" role="alert">'
                    + '<p><strong>Gene:</strong> '
                    + '<a href="' + row["gene_link"] + '">' + row["gene_name"] + '</a></p>'
                    + '<p>' + row["gene_description"] + '</p>'
                    + '<p><strong>Normalized phenotypic values (NPVs):</strong>'
                    + '<ul><li><a href="' + dataset1_link + '">' + str(dataset1) + '</a>: '
                    + '{:.2f}'.format(row[dataset1_id]) + '</li>'
                    + '<li><a href="' + dataset2_link + '">' + str(dataset2) + '</a>: '
                    + '{:.2f}'.format(row[dataset2_id]) + '</li></ul></p>'
                    + '</div>', axis=1
    )
    df_matrix.set_index("gene_name", inplace=True, drop=False)

    min_axis = np.floor(np.nanmin(df_matrix[[dataset1_id, dataset2_id]].min(axis=0)))
    max_axis = np.ceil(np.nanmax(df_matrix[[dataset1_id, dataset2_id]].max(axis=0)))

    values = df_matrix[[dataset1_id, dataset2_id, "tooltip"]].values.tolist()

    context = {
        "dataset1": dataset1,
        "dataset2": dataset2,
        "values": values,
        "min_axis": min_axis,
        "max_axis": max_axis,
        "similarity": similarity
    }
    return render(request, "datasets/scatterplot_gc.html", context)


@never_cache
@ratelimit(key="ip", rate=rl_rate, block=rl_block)
def scores(request, dataset_id):

    dataset = get_object_or_404(Dataset, pk=dataset_id)
    scores = dataset.get_scores().order_by("valuez")
    scores = update_values_with_percentile(scores, "valuez")

    context = {"dataset": dataset, "scores": scores}

    return render(request, "datasets/scores_min.html", context)


@ratelimit(key="ip", rate=rl_rate, block=rl_block)
def download_scores(request, dataset1_id, dataset2_id=None):

    dataset1 = get_object_or_404(Dataset, pk=dataset1_id)
    scores1 = dataset1.get_scores().order_by("valuez")

    expected_columns = ['gene_id', 'gene_systematic_name', 'gene_common_name', 'valuez']

    # If no scores retrieved, create an empty dataframe with the relevant fields
    if scores1.count() == 0:
        scores1_df = pd.DataFrame(columns=expected_columns)
    else:
        scores1_df = pd.DataFrame(list(scores1))

    if dataset2_id:
        dataset2 = get_object_or_404(Dataset, pk=dataset2_id)
        scores2 = dataset2.get_scores().order_by("valuez")
        if scores2.count() == 0:
            scores2_df = pd.DataFrame(columns=expected_columns)
        else:
            scores2_df = pd.DataFrame(list(scores2))

        scores_df = scores1_df.merge(scores2_df, how="outer", on="gene_id", suffixes=('_dataset1', '_dataset2'))
        scores_df = scores_df[['gene_id', 'gene_systematic_name_dataset1',
                               'gene_common_name_dataset1', 'valuez_dataset1', 'valuez_dataset2']]
        scores_df.columns = ['Gene ID', 'Gene systematic name', 'Gene common name',
                             'NPV ' + str(dataset1), 'NPV ' + str(dataset2)]
        filename = "%s_screen%d_screen%d_NPVs.txt" % (DOWNLOAD_PREFIX, dataset1_id, dataset2_id)
    else:
        scores_df = scores1_df
        scores_df = scores_df[['gene_id', 'gene_systematic_name', 'gene_common_name', 'valuez']]
        scores_df.columns = ['Gene ID', 'Gene systematic name', 'Gene common name', 'NPV ' + str(dataset1)]
        filename = "%s_screen%d_NPVs.txt" % (DOWNLOAD_PREFIX, dataset1_id)

    # Prepare the HttpResponse
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="%s"' % filename

    scores_df.to_csv(path_or_buf=response, sep="\t", index=False)

    return response


@ratelimit(key="ip", rate=rl_rate, block=rl_block)
def similarities(request, dataset_id):

    dataset = get_object_or_404(Dataset, pk=dataset_id)
    similarities = dataset.get_similarities().order_by("-score")
    similarities = update_values_with_percentile(similarities, "score")

    context = {
        "dataset": dataset,
        "similarities": similarities,
    }

    return render(request, "datasets/similarities_min.html", context)


@ratelimit(key="ip", rate=rl_rate, block=rl_block)
def download_similarities(request, dataset_id):

    dataset = get_object_or_404(Dataset, pk=dataset_id)
    similarities = dataset.get_similarities().order_by("-score")
    similarities_df = pd.DataFrame(list(similarities))
    similarities_df.columns = ['Correlation mean', 'Correlation std. dev.',
                               'Screen ID', 'Screen name']

    # Prepare the HttpResponse
    filename = "%s_screen%d_similarities.txt" % (DOWNLOAD_PREFIX, dataset_id)
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="%s"' % filename

    similarities_df.to_csv(path_or_buf=response, sep="\t", index=False)

    return response


@ratelimit(key="ip", rate=rl_rate, block=rl_block)
def download_observable_datasets_list(request, observable_id):
    """Download all datasets associated with an observable"""
    import pandas

    observable = get_object_or_404(Observable, pk=observable_id)

    filename = "%s_observable_datasets_list_%s.txt" % (
        settings.DOWNLOAD_PREFIX,
        observable_id,
    )

    datasets = (
        observable.datasets()
        .select_related("paper__latest_tested_status__status")
        .filter(paper__latest_data_status__status__name="loaded")
        .values_list("id", "name", "paper__pmid", "paper__latest_tested_status")
        .distinct()
    )
    df = pandas.DataFrame(datasets)
    df.columns = ["id", "name", "pmid", "latest_tested_status"]
    exported_file = os.path.join(tempfile.gettempdir(), filename)
    if not os.path.exists(exported_file):
        df.to_csv(exported_file, sep="\t", index=None)
    return send_file(exported_file)


@ratelimit(key="ip", rate=rl_rate, block=rl_block)
def download_dataset_scores(request, datasets=None, filename=None):
    """Downloads scores for one dataset or a list of datasets. Produces a gene x dataset matrix."""

    import pandas as pd
    import numpy as np

    # Dataset ids can be optionally provided
    datasets = datasets or []

    if not datasets:
        for key, value in request.GET.items():
            try:
                datasets.append(int(key))
            except:
                pass

    # Get all data as a list of dicts
    data = list(
        Data.objects.filter(dataset_id__in=datasets)
        .filter(dataset__data_source__release=True)
        .values()
    )

    # Transform data into a DataFrame (long form)
    data_df = pd.DataFrame(data)

    # Prepare the HttpResponse
    filename = filename or "%s_data.txt" % settings.DOWNLOAD_PREFIX
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="%s"' % filename

    # https://github.com/johnculviner/jquery.fileDownload/blob/master/src/Scripts/jquery.fileDownload.js#L11
    # If this is not set, callbacks do not work
    response["Set-Cookie"] = "fileDownload=true; path=/"

    # If there are no datasets, cut out early and return empty file
    if data_df.empty:
        data_df.to_csv(path_or_buf=response, sep="\t", na_rep="NaN")
        return response

    # Make sure that values are numeric
    data_df["valuez"] = data_df["valuez"].astype(float)

    # Pivot DataFrame from long to wide form
    data_matrix = pd.pivot_table(
        data_df,
        index="gene_id",
        columns="dataset_id",
        values="valuez",
        fill_value=np.nan,
    )

    # Replace gene_ids with ORF names
    genes = list(Gene.objects.filter(id__in=data_matrix.index.values).values())
    genes_df = pd.DataFrame(genes)
    genes_df.set_index("id", inplace=True)
    data_matrix.index = genes_df.reindex(index=data_matrix.index.values)[
        "systematic_name"
    ].values
    data_matrix.index.rename("ORF", inplace=True)

    # Replace dataset_ids with dataset names
    datasets = list(Dataset.objects.filter(id__in=data_matrix.columns.values).values())
    datasets_df = pd.DataFrame(datasets)
    datasets_df.set_index("id", inplace=True)
    data_matrix.columns = datasets_df.reindex(index=data_matrix.columns.values)[
        "name"
    ].values

    # Print data matrix to response buffer
    data_matrix.to_csv(path_or_buf=response, sep="\t", na_rep="NaN")

    return response


@ratelimit(key="ip", rate=rl_rate, block=rl_block)
def download_observable_datasets(request, observable_id):
    """Download all datasets associated with an observable"""

    observable = get_object_or_404(Observable, pk=observable_id)
    filename = "%s_observable_datasets_%s.txt" % (
        settings.DOWNLOAD_PREFIX,
        observable_id,
    )
    return download_dataset_scores(
        request, datasets=observable.datasets(), filename=filename
    )


@ratelimit(key="ip", rate=rl_rate, block=rl_block)
def download_paper_datasets(request, paper_id):
    """Download all datasets associated with a paper"""

    paper = get_object_or_404(Paper, pk=paper_id)
    filename = "%s_paper_data_%s.txt" % (settings.DOWNLOAD_PREFIX, paper.id)
    return download_dataset_scores(
        request, datasets=paper.dataset_set.all(), filename=filename
    )


@ratelimit(key="ip", rate=rl_rate, block=rl_block)
def download_condition_datasets(request, condition_id):
    """Download all datasets associated with a condition type"""

    condition = get_object_or_404(ConditionType, pk=condition_id)
    filename = "%s_condition_data_%s.txt" % (settings.DOWNLOAD_PREFIX, condition.id)
    return download_dataset_scores(
        request, datasets=condition.datasets(), filename=filename
    )


@ratelimit(key="ip", rate=rl_rate, block=rl_block)
def download_medium_datasets(request, medium_id):
    """Download all datasets associated with a medium"""

    medium = get_object_or_404(Medium, pk=medium_id)

    filename = "%s_medium_datasets_%s.txt" % (
        settings.DOWNLOAD_PREFIX,
        medium.display_name,
    )
    return download_dataset_scores(
        request, datasets=medium.datasets(), filename=filename
    )


@ratelimit(key="ip", rate=rl_rate, block=rl_block)
def data(request, domain, id):

    file_header = ""

    if domain == "papers":
        paper = get_object_or_404(Paper, pk=id)
        datasets = paper.dataset_set
        file_header = "# Paper: %s (PMID %s)\n" % (paper, paper.pmid)

    if domain == "datasets":
        # datasets = get_object_or_404(Dataset, pk=id)
        datasets = Dataset.objects.filter(pk=id)
        dataset = datasets.first()
        file_header = "# Paper: %s (PMID %s)\n# Dataset: %s\n" % (
            dataset.paper,
            dataset.paper.pmid,
            dataset,
        )

    if domain == "conditions":
        conditiontype = get_object_or_404(ConditionType, pk=id)
        datasets = conditiontype.datasets()
        file_header = "# Condition: %s (ID %s)\n" % (conditiontype, conditiontype.id)

    if domain == "chebi":
        chebi_entity = ChebiEntity("CHEBI:" + str(id))
        children = []
        for relation in chebi_entity.get_incomings():
            if relation.get_type() == "has_role":
                tid = relation.get_target_chebi_id()
                tid = int(filter(str.isdigit, tid))
                children.append(tid)
        datasets = Dataset.objects.filter(
            conditionset__conditions__type__chebi_id__in=children
        )
        file_header = "# Data for conditions annotated as %s (ChEBI:%s)\n" % (
            chebi_entity.get_name(),
            id,
        )

    if domain == "phenotypes":
        phenotype = get_object_or_404(Observable, pk=id)
        datasets = phenotype.datasets()
        file_header = "# Phenotype: %s (ID %s)\n" % (phenotype, phenotype.id)

    data = Data.objects.filter(dataset_id__in=datasets.values("id")).all()

    orfs = list(data.values_list("orf", flat=True).distinct())
    datasets_ids = list(
        data.values_list("dataset_id", flat=True).order_by("dataset__paper").distinct()
    )
    matrix = [[None] * len(datasets_ids) for i in orfs]

    for datapoint in data:
        i = orfs.index(datapoint.orf)
        j = datasets_ids.index(datapoint.dataset_id)
        matrix[i][j] = datapoint.value

    column_headers = (
        "\t"
        + "\t".join(
            [
                "%s" % get_object_or_404(Dataset, pk=dataset_id)
                for dataset_id in datasets_ids
            ]
        )
        + "\n"
    )

    data_row = []
    for i, orf in enumerate(orfs):
        new_row = orf + "\t" + "\t".join([str(val) for val in matrix[i]])
        data_row.append(new_row)

    txt3 = "\n".join(data_row)

    response = HttpResponse(
        file_header + column_headers + txt3, content_type="text/plain"
    )
    response["Content-Disposition"] = 'attachment; filename="%s_%s_%s_data.txt"' % (
        settings.DOWNLOAD_PREFIX,
        domain,
        id,
    )

    return response
