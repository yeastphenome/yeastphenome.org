from django.urls import path
from . import views

urlpatterns = [
    path("", views.gene_explorer, name="index"),
    path("<str:query>/", views.gene_detail, name="detail"),
    path("<str:gene_id>/download/", views.download_all, name="download_gene"),
    path(
        "<str:gene_id>/download/sims/",
        views.download_sims,
        name="download_sims",
    ),
    path("<str:gene_id>/similar/", views.similar_genes, name="similar_genes"),
    path(
        "<str:gene_id>/scores/",
        views.gene_datasets,
        name="datasets",
    ),
]

app_name = "genes"
