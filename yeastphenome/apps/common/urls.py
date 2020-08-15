from django.urls import path

from . import views
from . import graphs

urlpatterns = [
    path("", views.index, name="index"),
    path("about/", views.about, name="about"),
    path("getting-started/", views.getting_started, name="getting-started"),
    path("explorer/", views.data_explorer, name="explorer"),
    path("cart/", views.view_cart, name="view_cart"),
    path("cart/add/<str:dataset_id>/<str:next>", views.add_to_cart, name="add_to_cart"),
    path(
        "cart/remove/<str:dataset_id>/<str:next>",
        views.remove_from_cart,
        name="remove_from_cart",
    ),
    path("cart/clear/", views.clear_cart, name="clear_cart"),
    # Graphs
    path("graph/papers/yearly/", graphs.papers_by_year, name="papers-by-year"),
    path(
        "graph/dataset/<int:dataset_id>/collection/yearly/",
        graphs.collection_by_year,
        name="collection-by-year",
    ),
    path(
        "graph/papers/<int:paper_id>/citations/",
        graphs.paper_citation_graph,
        name="paper-citation-graph",
    ),
]

app_name = "common"
