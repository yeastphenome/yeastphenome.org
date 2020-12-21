from django.conf.urls import url
from django.urls import path
from . import views

urlpatterns = [
    path("", views.data_explorer, name="index"),
    path("class/<str:query>/", views.data_explorer_redirect, name="index"),
    path(
        "collection/<int:collection_id>/", views.data_explorer, name="collection_detail"
    ),
    path(
        "observable/<str:observable_id>/",
        views.download_observable_datasets,
        name="download_observable_datasets",
    ),
    path(
        "medium/<str:medium_id>/",
        views.download_medium_datasets,
        name="download_medium_datasets",
    ),
    path(
        "<int:dataset_id>/scores/",
        views.dataset_plot,
        name="dataset_plot",
    ),
    path(
        "<int:dataset_id>/similar/",
        views.similar_dataset_table,
        name="similar_dataset_table",
    ),
    path(
        "<int:dataset_id>/similar/download/",
        views.download_dataset_similarities,
        name="download_dataset_similarities",
    ),
    url(r"^(?P<domain>papers)/(?P<id>\d+)/", views.data, name="data"),
    url(r"^(?P<domain>datasets)/(?P<id>\d+)/", views.data, name="data"),
    url(r"^(?P<domain>conditions)/(?P<id>\d+)/", views.data, name="data"),
    url(r"^conditions/(?P<domain>chebi)/(?P<id>\d+)/", views.data, name="data"),
    url(r"^(?P<domain>phenotypes)/(?P<id>\d+)/", views.data, name="data"),
    url(r"^(?P<dataset_id>\d+)/$", views.dataset_detail, name="dataset_detail"),
    url(r"^download/$", views.download_dataset_scores, name="download_dataset_scores"),
    url(r"^download/cart/$", views.download_dataset_cart, name="download_dataset_cart"),
    url(r"^tag/(?P<id>\d+)/", views.tag, name="tag"),
]

app_name = "datasets"
