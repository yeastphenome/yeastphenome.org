from django.views.generic.base import TemplateView
from django.urls import path
from django.conf.urls import url

from . import views, search_views

urlpatterns = [
    path("", views.index, name="index"),
    path("about/", views.about, name="about"),
    path("support/", views.support, name="support"),
    path("about/project/", views.project, name="project"),
    path("about/stats/", views.stats, name="stats"),
    path("about/faq/", views.faq, name="faq"),
    path("explore/", views.explorer, name="explorer"),
    path("about/authors/", views.authors, name="contributors"),
    path(
        "about/data_contributors/",
        views.ContributorsListView.as_view(),
        name="data_contributors",
    ),
    path("downloads/cart/", views.view_cart, name="view_cart"),
    path("downloads/bundles/", views.download_bundles, name="download_bundles"),
    path("cart/add/<str:dataset_id>/", views.add_to_cart, name="add_to_cart"),
    path("cart/add/<str:dataset_id>/<str:next>", views.add_to_cart, name="add_to_cart"),
    path(
        "cart/add/conditiontype/<str:conditiontype_id>/datasets/",
        views.add_to_cart_by_conditiontype,
        name="add_to_cart_by_conditiontype",
    ),
    path(
        "cart/add/paper/<str:paper_id>/datasets/",
        views.add_to_cart_by_paper,
        name="add_to_cart_by_paper",
    ),
    path(
        "cart/add/medium/<str:medium_id>/datasets/",
        views.add_to_cart_by_medium,
        name="add_to_cart_by_medium",
    ),
    path(
        "cart/add/observable/<str:observable_id>/datasets/",
        views.add_to_cart_by_observable,
        name="add_to_cart_by_observable",
    ),
    path(
        "cart/remove/<str:dataset_id>/",
        views.remove_from_cart,
        name="remove_from_cart",
    ),
    path(
        "cart/remove/<str:dataset_id>/<str:next>",
        views.remove_from_cart,
        name="remove_from_cart",
    ),
    path("cart/clear/", views.clear_cart, name="clear_cart"),
    path("search/", search_views.index, name="search"),
    path("_ah/warmup/", views.warmup, name="warmup"),
    url(
        r"^robots\.txt/$",
        TemplateView.as_view(
            template_name="base/robots.txt", content_type="text/plain"
        ),
    ),
]

app_name = "common"
