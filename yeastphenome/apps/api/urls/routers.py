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
    path("genes/", views.GetGenes.as_view(), name="get_genes"),
    path("genes/<str:systematic_name>/similar", views.GetSimilarGenes.as_view()),
    path(
        "observable/<int:observable_id>/datasets",
        views.GetObservableDatasets.as_view(),
        name="observable_datasets",
    ),
    path(
        "medium/<int:medium_id>/datasets",
        views.GetMediumDatasets.as_view(),
        name="medium_datasets",
    ),
    path(
        "tag/<int:tag_id>/conditiontypes",
        views.GetTagConditionTypes.as_view(),
        name="tag_condition_types",
    ),
    path(
        "conditiontype/<int:conditiontype_id>/datasets/",
        views.GetConditionTypeDatasets.as_view(),
        name="conditiontype_datasets",
    ),
    path(
        "genes/datasets/<str:systematic_name>/",
        views.GetGeneDatasets.as_view(),
        name="gene_datasets",
    ),
    path(
        "genes/<str:systematic_name>/<int:N>/similar", views.GetSimilarGenes.as_view()
    ),
    path(
        "genes/<str:systematic_name>/<int:N>/similar/<int:reverse>",
        views.GetSimilarGenes.as_view(),
    ),
    path(
        "search/datasets/explore",
        views.DatasetsSearch.as_view(),
        name="datasets_search",
    ),
    path(
        "search/conditions/explorr",
        views.ConditionsSearch.as_view(),
        name="conditions_search",
    ),
    path("search/papers/explore", views.PapersSearch.as_view(), name="papers_search"),
    path(
        "search/phenotypes/explore",
        views.PhenotypesSearch.as_view(),
        name="phenotypes_search",
    ),
    path("api-auth/", include("rest_framework.urls", namespace="rest_framework")),
    path("api-token-auth/", authviews.obtain_auth_token),
]
