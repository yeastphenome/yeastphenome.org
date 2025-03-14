from django.urls import path

from . import views

urlpatterns = [
    path("", views.index, name="index"),
    path("<int:phenotype_id>/", views.phenotype_detail, name="detail"),
    path("<int:phenotype_id>/screens/", views.phenotype_datasets, name="datasets"),
]

app_name = "phenotypes"
