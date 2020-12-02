from django.urls import path
from yeastphenome import settings

from . import views

urlpatterns = [
    path("", views.paper_explorer, name="all"),
    path("year/<int:year>/", views.paper_explorer, name="all_year"),
    path("<int:pk>/", views.PaperDetailView.as_view(), name="detail"),
    # Data
    path(
        "<int:paper_id>/%s_<int:pmid>_datasets_list.txt" % settings.DOWNLOAD_PREFIX,
        views.paper_datasets,
        name="paper_datasets",
    ),
]

app_name = "papers"
