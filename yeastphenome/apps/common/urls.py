from django.urls import path

from . import views
from . import graphs

urlpatterns = [
    path("", views.index, name="index"),
    path("about/", views.about, name="about"),
    path("stats/", views.stats, name="stats"),
    path("faq/", views.faq, name="faq"),
    path("contributors/", views.contributors, name="contributors"),
    path("cart/", views.view_cart, name="view_cart"),
    path("cart/add/<str:dataset_id>/<str:next>", views.add_to_cart, name="add_to_cart"),
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
        "graph/papers/network/",
        graphs.paper_citation_graph_neo4j,
        name="paper-citation-graph-neo4j",
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
        "graph/dataset/sources/", graphs.dataset_sources, name="dataset-sources-graph",
    ),
]

urlpatterns += graphs

app_name = "common"
