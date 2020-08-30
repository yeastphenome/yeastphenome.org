from django.conf.urls import url

from rest_framework import permissions
from .routers import urlpatterns as router_urls

from drf_yasg.views import get_schema_view
from drf_yasg import openapi
from yeastphenome.settings import HELP_CONTACT_EMAIL

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
    permission_classes=(permissions.AllowAnyGet,),
)

urlpatterns = [
    url(r"^schema/$", schema_view, name="api-schema"),
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
    url(r"^docs/$", schema_view.with_ui("redoc", cache_timeout=0), name="schema-redoc"),
]

urlpatterns += router_urls
app_name = "api"
