from django.conf.urls import url
from django.urls import path
from . import views

urlpatterns = [
    path("", views.data_explorer, name="index"),
    path(
        "collection/<int:collection_id>/", views.data_explorer, name="collection_detail"
    ),
    path("genes", views.gene_explorer, name="genes"),
    path("download/<str:systematic_name>/", views.download_all, name="download_gene"),
    path(
        "gene/download/sims/<str:systematic_name>/",
        views.download_sims,
        name="download_sims",
    ),
    path(
        "gene/similar/<str:systematic_name>/", views.similar_genes, name="similar_genes"
    ),
    path(
        "gene/datasets/<str:systematic_name>/",
        views.gene_datasets,
        name="gene_datasets",
    ),
    url(r"^(?P<domain>papers)/(?P<id>\d+)/", views.data, name="data"),
    url(r"^(?P<domain>datasets)/(?P<id>\d+)/", views.data, name="data"),
    url(r"^(?P<domain>conditions)/(?P<id>\d+)/", views.data, name="data"),
    url(r"^conditions/(?P<domain>chebi)/(?P<id>\d+)/", views.data, name="data"),
    url(r"^(?P<domain>phenotypes)/(?P<id>\d+)/", views.data, name="data"),
    url(r"^(?P<pk>\d+)/$", views.DatasetDetailView.as_view(), name="detail"),
    url(r"^download/$", views.download, name="download"),
    url(r"^tag/(?P<id>\d+)/", views.tag, name="tag"),
]

app_name = "datasets"
