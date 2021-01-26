from django.urls import path
from . import views

urlpatterns = [
    path("", views.gene_explorer, name="index"),
    path("<int:gene_id>/", views.gene_detail, name="detail"),
    path("<int:gene_id>/similar/", views.similar_genes, name="similar_genes"),
    path(
        "<int:gene1_id>/similar/<int:gene2_id>/",
        views.similar_scatterplot,
        name="similar_scatterplot",
    ),
    path(
        "<int:gene_id>/similar/download/",
        views.download_gene_similarities,
        name="download_gene_similarities",
    ),
    path("<int:gene_id>/scores/", views.gene_datasets, name="datasets"),
    path(
        "<int:gene_id>/scores/download/",
        views.download_gene_scores,
        name="download_gene_scores",
    ),
]

app_name = "genes"
