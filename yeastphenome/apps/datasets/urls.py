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
        "table/<int:dataset_id>/scores/",
        views.dataset_plot,
        name="dataset_plot",
    ),
    path(
        "table/<int:dataset_id>/similar/",
        views.similar_dataset_table,
        name="similar_dataset_table",
    ),
    url(r"^(?P<domain>papers)/(?P<id>\d+)/", views.data, name="data"),
    url(r"^(?P<domain>datasets)/(?P<id>\d+)/", views.data, name="data"),
    url(r"^(?P<domain>conditions)/(?P<id>\d+)/", views.data, name="data"),
    url(r"^conditions/(?P<domain>chebi)/(?P<id>\d+)/", views.data, name="data"),
    url(r"^(?P<domain>phenotypes)/(?P<id>\d+)/", views.data, name="data"),
    url(r"^(?P<pk>\d+)/$", views.DatasetDetailView.as_view(), name="detail"),
    url(r"^download/$", views.download, name="download"),
    url(r"^download/all/$", views.download_all, name="download_all"),
    path(
        "download/similar/<int:dataset_id>/",
        views.download_dataset_sims,
        name="download_dataset_sims",
    ),
    url(r"^tag/(?P<id>\d+)/", views.tag, name="tag"),
]

app_name = "datasets"
