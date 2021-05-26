from django.urls import path
from yeastphenome import settings

from . import views

urlpatterns = [
    path("", views.paper_explorer, name="all"),
    path("year/<int:year>/", views.paper_explorer, name="all_year"),
    path("<int:paper_id>/", views.paper_detail, name="detail"),
    path("<int:paper_id>/datasets/", views.paper_datasets, name="datasets"),
    path("graph/yearly/", views.papers_by_year, name="papers-by-year"),
    # Data
    path(
        "<int:paper_id>/%s_<int:pmid>_datasets_list.txt" % settings.DOWNLOAD_PREFIX,
        views.paper_datasets_list,
        name="paper_datasets_list",
    ),
]

app_name = "papers"
