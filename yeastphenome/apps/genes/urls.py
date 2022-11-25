from django.urls import path
from . import views

urlpatterns = [
    path("", views.index, name="index"),
    path("<int:gene_id>/", views.detail, name="detail"),
    path("<int:gene_id>/scores/", views.scores, name="scores"),
    path("<int:gene1_id>/scores/download/", views.download_scores, name="download_scores"),
    path("<int:gene_id>/similarities/", views.similarities, name="similarities"),
    path("<int:gene_id>/similarities/download/", views.download_similarities, name="download_similarities"),
    path("<int:gene1_id>/similarities/<int:gene2_id>/", views.scatterplot_gc, name="scatterplot_gc"),
    path("<int:gene1_id>/similarities/<int:gene2_id>/download/", views.download_scores, name="download_scores_for_pair"),
]

app_name = "genes"
