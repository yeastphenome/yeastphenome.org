from django.conf.urls import url
from django.urls import path

from . import views

urlpatterns = [
    url(r"^$", views.index, name="index"),
    path("<int:phenotype_id>/", views.phenotype_detail, name="detail"),
    path("<int:phenotype_id>/datasets/", views.phenotype_datasets, name="datasets"),
]

app_name = "phenotypes"
