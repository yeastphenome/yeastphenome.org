from django.conf.urls import url
from django.urls import path

from drf_yasg.views import get_schema_view
from drf_yasg import openapi
from yeastphenome.settings import HELP_CONTACT_EMAIL

import yeastphenome.apps.api.conditions as conditions_views
import yeastphenome.apps.api.papers as papers_views
import yeastphenome.apps.api.datasets as datasets_views
import yeastphenome.apps.api.genes as genes_views
import yeastphenome.apps.api.phenotypes as phenotypes_views
import yeastphenome.apps.api.search as search_views

from .permissions import AllowAnyGet

# Documentation URL
schema_view = get_schema_view(
    openapi.Info(
        title="YeastPhenome API",
        default_version="v1",
        description="Programmatic functions for YeastPhenome.org",
        #      terms_of_service="https://www.google.com/policies/terms/",
        contact=openapi.Contact(email=HELP_CONTACT_EMAIL),
        license=openapi.License(name="Apache License"),
    ),
    public=True,
    permission_classes=(AllowAnyGet,),
)

urlpatterns = [
    url(
        r"^swagger(?P<format>\.json|\.yaml)$",
        schema_view.without_ui(cache_timeout=0),
        name="schema-json",
    ),
    url(
        r"^swagger/$",
        schema_view.with_ui("swagger", cache_timeout=0),
        name="schema-swagger-ui",
    ),
    path(
        "observable/<int:observable_id>/datasets",
        phenotypes_views.GetObservableDatasets.as_view(),
        name="observable_datasets",
    ),
    # Explorer Server Side Rendering Queries
    path(
        "explorer/phenotypes",
        phenotypes_views.RunPhenotypesQuery.as_view(),
        name="phenotypes_query",
    ),
    path(
        "explorer/genes",
        genes_views.RunGenesQuery.as_view(),
        name="genes_query",
    ),
    path(
        "explorer/conditions",
        conditions_views.RunConditionsQuery.as_view(),
        name="conditions_query",
    ),
    path(
        "explorer/<int:collection_id>/datasets",
        datasets_views.RunDatasetsQuery.as_view(),
        name="datasets_query",
    ),
    path(
        "explorer/datasets",
        datasets_views.RunDatasetsQuery.as_view(),
        name="datasets_query",
    ),
    path(
        "explorer/papers",
        papers_views.RunPapersQuery.as_view(),
        name="papers_query",
    ),
    # Datasets Tables specific to models
    path(
        "medium/<int:medium_id>/datasets",
        conditions_views.GetMediumDatasets.as_view(),
        name="medium_datasets",
    ),
    path(
        "paper/<int:paper_id>/datasets",
        papers_views.GetPaperDatasets.as_view(),
        name="paper_datasets",
    ),
    path(
        "cart/datasets",
        datasets_views.GetCartDatasets.as_view(),
        name="cart_datasets",
    ),
    path(
        "tag/<int:tag_id>/conditiontypes",
        conditions_views.GetTagConditionTypes.as_view(),
        name="tag_condition_types",
    ),
    path(
        "conditiontype/<int:conditiontype_id>/datasets/",
        conditions_views.GetConditionTypeDatasets.as_view(),
        name="conditiontype_datasets",
    ),
    path("genes/", genes_views.GetGenes.as_view(), name="get_genes"),
    path("genes/<int:gene_id>/similar/", genes_views.GetSimilarGenes.as_view()),
    path(
        "genes/datasets/<int:gene_id>/",
        genes_views.GetGeneDatasets.as_view(),
        name="gene_datasets",
    ),
    path(
        "genes/<int:gene_id>/<int:N>/similar/",
        genes_views.GetSimilarGenes.as_view(),
    ),
    path(
        "genes/<int:gene_id>/<int:N>/similar/<int:reverse>/",
        genes_views.GetSimilarGenes.as_view(),
    ),
    path(
        "search/datasets/explore",
        search_views.DatasetsSearch.as_view(),
        name="datasets_search",
    ),
    path(
        "search/conditions/explore",
        search_views.ConditionsSearch.as_view(),
        name="conditions_search",
    ),
    path(
        "search/papers/explore",
        search_views.PapersSearch.as_view(),
        name="papers_search",
    ),
    path(
        "search/phenotypes/explore",
        search_views.PhenotypesSearch.as_view(),
        name="phenotypes_search",
    ),
]


app_name = "api"
