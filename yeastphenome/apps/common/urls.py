from django.views.generic.base import TemplateView
from django.urls import path
from django.conf.urls import url

from . import views
from . import graphs

urlpatterns = [
    path("", views.index, name="index"),
    path("about/", views.about, name="about"),
    path("about/stats/", views.stats, name="stats"),
    path("about/faq/", views.faq, name="faq"),
    path("explore/", views.explorer, name="explorer"),
    path("about/contributors/", views.contributors, name="contributors"),
    path(
        "about/data_contributors/",
        views.ContributorsListView.as_view(),
        name="data_contributors",
    ),
    path("cart/", views.view_cart, name="view_cart"),
    path("cart/add/<str:dataset_id>/", views.add_to_cart, name="add_to_cart"),
    path("cart/add/<str:dataset_id>/<str:next>", views.add_to_cart, name="add_to_cart"),
    path(
        "cart/add/conditiontype/<str:conditiontype_id>/datasets/",
        views.add_to_cart_by_conditiontype,
        name="add_to_cart_by_conditiontype",
    ),
    path(
        "cart/add/medium/<str:medium_id>/datasets/",
        views.add_to_cart_by_medium,
        name="add_to_cart_by_medium",
    ),
    path(
        "cart/add/observable/<str:observable_id>/datasets/",
        views.add_to_cart_by_observable,
        name="add_to_cart_by_observable",
    ),
    path(
        "cart/remove/<str:dataset_id>/",
        views.remove_from_cart,
        name="remove_from_cart",
    ),
    path(
        "cart/remove/<str:dataset_id>/<str:next>",
        views.remove_from_cart,
        name="remove_from_cart",
    ),
    path("cart/clear/", views.clear_cart, name="clear_cart"),
    # Getting Started
    path("getting-started/", views.getting_started, name="getting-started"),
    path("getting-started/introduction/", views.introduction, name="introduction"),
    path("getting-started/background/", views.background, name="background"),
    path("getting-started/advanced/", views.advanced, name="advanced"),
    path("getting-started/tutorials/", views.tutorials, name="tutorials"),
    path("_ah/warmup/", views.warmup, name="warmup"),
    url(
        r"^robots\.txt/$",
        TemplateView.as_view(
            template_name="base/robots.txt", content_type="text/plain"
        ),
    ),
]

# Graphs

graphs = [
    path("graph/papers/yearly/", graphs.papers_by_year, name="papers-by-year"),
    path(
        "graph/dataset/<int:dataset_id>/collection/yearly/",
        graphs.collection_by_year,
        name="collection-by-year",
    ),
    path(
        "graph/papers/citations/explorable/",
        graphs.paper_citation_graph_explorable,
        name="paper-citation-graph-explorable",
    ),
    path(
        "graph/papers/citations/",
        graphs.papers_citation_graph,
        name="papers-citation-graph",
    ),
    path(
        "graph/papers/<int:paper_id>/citations/",
        graphs.paper_citation_graph,
        name="paper-citation-graph",
    ),
    path(
        "graph/phenotypes/measurements/",
        graphs.phenotype_measurements,
        name="phenotype-measurements-graph",
    ),
    path(
        "graph/dataset/sources/",
        graphs.dataset_sources,
        name="dataset-sources-graph",
    ),
    path(
        "graph/dataset/genes/",
        graphs.dataset_genes,
        name="dataset-genes-graph",
    ),
    path(
        "graph/dataset/genes/<int:dataset_id>/",
        graphs.dataset_genes,
        name="dataset-genes-graph",
    ),
]

urlpatterns += graphs

app_name = "common"
