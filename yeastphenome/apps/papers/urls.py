from django.urls import path
from yeastphenome import settings

from . import views

urlpatterns = [
    path("<int:paper_id>/", views.detail, name="detail"),
    path("<int:paper_id>/datasets/", views.datasets, name="datasets"),
    path(
        "<int:paper_id>/%s_<int:pmid>_datasets_list.txt" % settings.DOWNLOAD_PREFIX,
        views.datasets_list,
        name="datasets_list",
    ),
]

app_name = "papers"
