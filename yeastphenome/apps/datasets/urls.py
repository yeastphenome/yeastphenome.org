from django.conf.urls import url
from django.urls import path
from . import views

urlpatterns = [
    path("", views.data_explorer, name="index"),
    path("genes", views.gene_explorer, name="genes"),
    url(r"^(?P<domain>papers)/(?P<id>\d+)/", views.data, name="data"),
    url(r"^(?P<domain>datasets)/(?P<id>\d+)/", views.data, name="data"),
    url(r"^(?P<domain>conditions)/(?P<id>\d+)/", views.data, name="data"),
    url(r"^conditions/(?P<domain>chebi)/(?P<id>\d+)/", views.data, name="data"),
    url(r"^(?P<domain>phenotypes)/(?P<id>\d+)/", views.data, name="data"),
    url(r"^(?P<pk>\d+)/$", views.DatasetDetailView.as_view(), name="detail"),
    url(r"^download/all/", views.download_all, name="download_all"),
    url(r"^download/", views.download, name="download"),
    url(r"^tag/(?P<id>\d+)/", views.tag, name="tag"),
]

app_name = "datasets"
