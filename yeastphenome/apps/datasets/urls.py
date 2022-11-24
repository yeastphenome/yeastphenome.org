from django.conf.urls import url
from django.urls import path
from . import views

urlpatterns = [
    path("", views.index, name="index"),
    path("<int:dataset_id>/", views.detail, name="detail"),
    path(
        "<int:dataset_id>/scores/",
        views.scores,
        name="scores",
    ),
    path(
        "<int:dataset_id>/similarities/",
        views.similarities,
        name="similarities",
    ),
    path(
        "<int:dataset1_id>/similarities/<int:dataset2_id>/",
        views.scatterplot,
        name="scatterplot",
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
]

app_name = "datasets"
