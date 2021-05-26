from django.conf.urls import url
from django.urls import path
from . import views

urlpatterns = [
    path("", views.data_explorer, name="index"),
    path("<int:dataset_id>/", views.dataset_detail, name="detail"),
    path(
        "<int:dataset_id>/scores/",
        views.dataset_scores,
        name="scores",
    ),
    path(
        "<int:dataset_id>/similarities/",
        views.dataset_similarities,
        name="similarities",
    ),
    path("class/<str:query>/", views.data_explorer_redirect, name="index"),
    path(
        "collection/<int:collection_id>/", views.data_explorer, name="collection_detail"
    ),
    path(
        "condition/<str:condition_id>/",
        views.download_condition_datasets,
        name="download_condition_datasets",
    ),
    path(
        "observable/<str:observable_id>/",
        views.download_observable_datasets,
        name="download_observable_datasets",
    ),
    path(
        "paper/<str:paper_id>/",
        views.download_paper_datasets,
        name="download_paper_datasets",
    ),
    path(
        "medium/<str:medium_id>/",
        views.download_medium_datasets,
        name="download_medium_datasets",
    ),
    path(
        "<int:dataset1_id>/similar/<int:dataset2_id>/",
        views.similar_scatterplot,
        name="similar_scatterplot",
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
    url(r"^download/$", views.download_dataset_scores, name="download_dataset_scores"),
    url(r"^download/cart/$", views.download_dataset_cart, name="download_dataset_cart"),
    url(r"^tag/(?P<id>\d+)/", views.tag, name="tag"),
]

app_name = "datasets"
