from django.views.generic.base import TemplateView
from django.urls import path
from django.conf.urls import url

from . import views

urlpatterns = [
    path("", views.index, name="index"),
    path("support/", views.support, name="support"),
    path("about/", views.about, name="about"),
    path("about/project/", views.project, name="project"),
    path("about/stats/", views.stats, name="stats"),
    path("about/faq/", views.faq, name="faq"),
    path("about/authors/", views.authors, name="contributors"),
    path(
        "about/data_contributors/",
        views.data_contributors,
        name="data_contributors",
    ),
    path("_ah/warmup/", views.warmup, name="warmup"),
    url(
        r"^robots\.txt/$",
        TemplateView.as_view(
            template_name="base/robots.txt", content_type="text/plain"
        ),
    ),
]

app_name = "common"
