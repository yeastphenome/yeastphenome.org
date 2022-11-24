from django.shortcuts import render, redirect
from django.shortcuts import get_object_or_404, reverse

from yeastphenome.apps.datasets.models import Data, Dataset
from yeastphenome.apps.genes.models import Gene
from yeastphenome.apps.common.utils_format import update_values_with_percentile

from ratelimit.decorators import ratelimit
from yeastphenome.settings import (
    VIEW_RATE_LIMIT as rl_rate,
    VIEW_RATE_LIMIT_BLOCK as rl_block,
)

import pandas as pd
import numpy as np
import plotly.graph_objects as go


@ratelimit(key="ip", rate=rl_rate, block=rl_block)
def index(request):
    return redirect("search:search")


@ratelimit(key="ip", rate=rl_rate, block=rl_block)
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

    similarities = gene.get_similarities()
    num_similarities = similarities.count()
    similarities_lowest = update_values_with_percentile(
        similarities.order_by("score"), "score"
    )[:10]
    similarities_highest = update_values_with_percentile(
        similarities.order_by("-score"), "score"
    )[:10]

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


@ratelimit(key="ip", rate=rl_rate, block=rl_block)
def scores(request, gene_id):

    gene = get_object_or_404(Gene, pk=gene_id)
    scores = gene.get_scores().order_by("valuez")
    scores = update_values_with_percentile(scores, "valuez")

    context = {
        "gene": gene,
        "scores": scores,
    }

    return render(request, "genes/scores_min.html", context)


@ratelimit(key="ip", rate=rl_rate, block=rl_block)
def similarities(request, gene_id):

    gene = get_object_or_404(Gene, pk=gene_id)
    similarities = gene.get_similarities().order_by("-score")
    similarities = update_values_with_percentile(similarities, "score")

    context = {
        "gene": gene,
        "similarities": similarities,
    }

    return render(request, "genes/similarities_min.html", context)


@ratelimit(key="ip", rate=rl_rate, block=rl_block)
def scatterplot(request, gene1_id, gene2_id):

    gene1 = get_object_or_404(Gene, pk=gene1_id)
    gene2 = get_object_or_404(Gene, pk=gene2_id)

    data = Data.objects.all_valid().filter(gene_id__in=[gene1_id, gene2_id])
    data = data.values("gene_id", "dataset_id", "valuez")

    df = pd.DataFrame(list(data))
    df = df.loc[df["valuez"].notnull()]
    df["valuez"] = pd.to_numeric(df["valuez"])

    df_matrix = pd.pivot_table(
        df, index="dataset_id", columns="gene_id", values="valuez"
    )

    datasets = Dataset.objects.all_valid().values("id", "name")
    datasets_df = pd.DataFrame(list(datasets))

    datasets_df["name2"] = datasets_df["name"].apply(
        lambda x: "<br>".join(x.split(" | "))
    )

    datasets_df["link"] = datasets_df.apply(
        lambda row: reverse("datasets:detail", args=[row["id"]]), axis=1
    )
    datasets_df["dataset_link"] = datasets_df.apply(
        lambda row: '<a href="' + row["link"] + '">' + row["name2"] + "</a>", axis=1
    )
    datasets_df.set_index("id", inplace=True)

    df_matrix["dataset_name"] = datasets_df["name"]
    df_matrix["dataset_name2"] = datasets_df["name2"]
    df_matrix["dataset_link"] = datasets_df["dataset_link"]

    df_matrix.set_index("dataset_name", inplace=True, drop=False)

    min_axis = np.floor(np.nanmin(df_matrix[[gene1_id, gene2_id]].min(axis=0)))
    max_axis = np.ceil(np.nanmax(df_matrix[[gene2_id, gene2_id]].max(axis=0)))

    fig = go.Figure()

    scatter = go.Scatter(
        x=df_matrix[gene1_id],
        y=df_matrix[gene2_id],
        text=df_matrix["dataset_name2"],
        mode="markers",
        marker=dict(size=10, opacity=0.5),
        name="Normalized phenotypic scores",
        hovertemplate="<b>%{text}</b><br><br>"
        + "x: %{x}<br>"
        + "y: %{y}<br><br>"
        + "(Click for more info)"
        "<extra></extra>",
    )
    fig.add_trace(scatter)

    xy = go.Scatter(
        x=[min_axis, max_axis], y=[min_axis, max_axis], mode="lines", name="y=x"
    )
    fig.add_trace(xy)

    annotations = [
        dict(
            xclick=df_matrix.loc[dataset_name, gene1_id],
            yclick=df_matrix.loc[dataset_name, gene2_id],
            x=max_axis + 1,
            y=(max_axis + min_axis) / 2,
            xanchor="left",
            yanchor="middle",
            text=df_matrix.loc[dataset_name, "dataset_link"],
            align="left",
            bgcolor="white",
            visible=False,
            showarrow=False,
            clicktoshow="onout",
        )
        for dataset_name in df_matrix["dataset_name"].values
    ]
    fig.update_layout(margin=dict(r=300, b=300), annotations=annotations)

    num_ticks = 10
    dtick = np.int((max_axis - min_axis) / num_ticks)
    tickvals = np.concatenate(
        (np.arange(0, min_axis, -dtick), np.arange(0, max_axis, dtick))
    )

    fig.update_xaxes(
        range=[min_axis - 1, max_axis + 1],
        tickvals=tickvals,
        showgrid=True,
        title_text=str(gene1),
    )
    fig.update_yaxes(
        range=[min_axis - 1, max_axis + 1],
        tickvals=tickvals,
        showgrid=True,
        scaleanchor="x",
        scaleratio=1,
        title_text=str(gene2),
    )
    fig.update_layout(
        template="simple_white",
        hovermode="closest",
        hoverlabel=dict(
            bgcolor="white",
            bordercolor="#2471A3",
            font=dict(
                color="black",
            ),
        ),
        showlegend=False,
        legend=dict(yanchor="top", y=0.99, xanchor="left", x=0.01),
    )

    graph = fig.to_html(full_html=False, default_height=900, default_width=900)

    context = {
        "gene": gene1,
        "gene2": gene2,
        "graph": graph,
    }
    return render(request, "genes/scatterplot.html", context)
