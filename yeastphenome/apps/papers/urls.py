from django.conf.urls import url
from yeastphenome import settings

from . import views

urlpatterns = [
    url(r"^$", views.paper_list_view, name="all"),
    url(r"^(?P<pk>\d+)/$", views.PaperDetailView.as_view(), name="detail"),
    # Data
    url(
        r"^(?P<paper_id>\d+)/%s_(?P<paper_pmid>\d+).zip$" % settings.DOWNLOAD_PREFIX,
        views.download_zip,
        name="download_zip",
    ),
    url(
        r"^(?P<paper_id>\d+)/%s_(\d+)_datasets_list.txt$" % settings.DOWNLOAD_PREFIX,
        views.paper_datasets,
        name="paper_datasets",
    ),
]

app_name = "papers"
