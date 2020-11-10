from django.urls import path
from . import views

urlpatterns = [
    path("", views.gene_explorer, name="index"),
    path("detail/<str:query>/", views.gene_detail, name="detail"),
    path("download/<str:systematic_name>/", views.download_all, name="download_gene"),
    path(
        "download/sims/<str:systematic_name>/",
        views.download_sims,
        name="download_sims",
    ),
    path("similar/<str:systematic_name>/", views.similar_genes, name="similar_genes"),
    path(
        "datasets/<str:systematic_name>/",
        views.gene_datasets,
        name="datasets",
    ),
]

app_name = "genes"
