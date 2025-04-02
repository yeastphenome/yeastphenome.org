from django.urls import path, re_path
from . import views

urlpatterns = [
    path("", views.index, name="index"),
    path("<int:dataset_id>/", views.detail, name="detail"),
    path("<int:dataset_id>/scores/", views.scores, name="scores"),
    path("<int:dataset1_id>/scores/download/", views.download_scores, name="download_scores"),
    path("<int:dataset_id>/similarities/", views.similarities, name="similarities"),
    path("<int:dataset_id>/similarities/download/", views.download_similarities, name="download_similarities"),
    path("<int:dataset1_id>/similarities/<int:dataset2_id>/", views.scatterplot_gc, name="scatterplot_gc"),
    path("<int:dataset1_id>/similarities/<int:dataset2_id>/download/", views.download_scores, name="download_scores_for_pair"),

    # re_path(r"^(?P<domain>papers)/(?P<id>\d+)/", views.data, name="data"),
    # re_path(r"^(?P<domain>datasets)/(?P<id>\d+)/", views.data, name="data"),
    # re_path(r"^(?P<domain>conditions)/(?P<id>\d+)/", views.data, name="data"),
    # re_path(r"^conditions/(?P<domain>chebi)/(?P<id>\d+)/", views.data, name="data"),
    # re_path(r"^(?P<domain>phenotypes)/(?P<id>\d+)/", views.data, name="data"),
]

app_name = "datasets"
