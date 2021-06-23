from django.urls import path
from . import views

urlpatterns = [
    path("<int:gene_id>/", views.detail, name="detail"),
    path("<int:gene_id>/scores/", views.scores, name="scores"),
    path("<int:gene_id>/similarities/", views.similarities, name="similarities"),
    path(
        "<int:gene1_id>/similarities/<int:gene2_id>/",
        views.scatterplot,
        name="scatterplot",
    ),
]

app_name = "genes"
