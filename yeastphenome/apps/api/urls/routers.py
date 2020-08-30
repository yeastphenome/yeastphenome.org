from django.urls import path
from django.conf.urls import include
import rest_framework.authtoken.views as authviews

from rest_framework import routers
import yeastphenome.apps.api.urls.serializers as views

router = routers.DefaultRouter()
router.register(r"^papers", views.PaperViewSet, basename="paper")

urlpatterns = [
    path("", include(router.urls)),
    path("papers/<int:paper_id>/references", views.GetPaperReferences.as_view()),
    path(
        "search/datasets/explorer",
        views.DatasetsSearch.as_view(),
        name="datasets_search",
    ),
    path("search/papers/explorer", views.PapersSearch.as_view(), name="papers_search"),
    path("api-auth/", include("rest_framework.urls", namespace="rest_framework")),
    path("api-token-auth/", authviews.obtain_auth_token),
]
