from django.urls import path

from . import views

urlpatterns = [
    path("<int:conditiontype_id>/", views.conditiontype_detail, name="detail"),
    path("<int:conditiontype_id>/datasets/", views.conditiontype_datasets, name="datasets"),
]

app_name = "conditions"
