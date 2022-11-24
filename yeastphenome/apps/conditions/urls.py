from django.urls import path

from . import views

urlpatterns = [
    path("", views.index, name="index"),
    path("<int:conditiontype_id>/", views.detail, name="detail"),
    path("<int:conditiontype_id>/datasets/", views.datasets, name="datasets"),
]

app_name = "conditions"
