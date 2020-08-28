from django.urls import path
from yeastphenome import settings

from . import views

urlpatterns = [
    path("", views.paper_explorer, name="all"),
    path("<int:pk>", views.PaperDetailView.as_view(), name="detail"),
    path("contributors/", views.ContributorsListView.as_view(), name="contributors"),
    # Data
    path(
        "<int:paper_id>/%s_<int:paper_pmid>.zip" % settings.DOWNLOAD_PREFIX,
        views.download_zip,
        name="download_zip",
    ),
    path(
        "<int:paper_id>/%s_(\d+)_datasets_list.txt" % settings.DOWNLOAD_PREFIX,
        views.paper_datasets,
        name="paper_datasets",
    ),
]

app_name = "papers"
