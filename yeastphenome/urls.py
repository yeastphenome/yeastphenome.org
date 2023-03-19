from django.conf.urls import include, url
from django.contrib import admin
from django.views.generic.base import TemplateView
from django.contrib.sitemaps import views
from django.urls import path

from yeastphenome.apps.papers import urls as papers_urls
from yeastphenome.apps.common import urls as common_urls
from yeastphenome.apps.phenotypes import urls as phenotypes_urls
from yeastphenome.apps.conditions import urls as conditions_urls
from yeastphenome.apps.datasets import urls as datasets_urls
from yeastphenome.apps.genes import urls as gene_urls
from yeastphenome.apps.search import urls as search_urls
from yeastphenome.apps.downloads import urls as downloads_urls

from yeastphenome.apps.papers.sitemap import PaperSitemap
from yeastphenome.apps.conditions.sitemap import ConditionTypeSitemap
from yeastphenome.apps.datasets.sitemap import DatasetSitemap
from yeastphenome.apps.genes.sitemap import GeneSitemap
from yeastphenome.apps.phenotypes.sitemap import ObservableSitemap
from yeastphenome.apps.common.sitemap import CommonSitemap

sitemaps = {'papers': PaperSitemap,
            'conditions': ConditionTypeSitemap,
            'datasets': DatasetSitemap,
            'genes': GeneSitemap,
            'phenotypes': ObservableSitemap,
            'common': CommonSitemap}

# Custom 404 page
handler404 = "yeastphenome.apps.common.views.handler404"

admin.autodiscover()

urlpatterns = [
    url(r"^admin/", admin.site.urls),
    url(r"^", include(common_urls, namespace="common")),
    url(r"^search/", include(search_urls, namespace="search")),
    url(r"^downloads/", include(downloads_urls, namespace="downloads")),
    url(r"^papers/", include(papers_urls, namespace="papers")),
    url(r"^phenotypes/", include(phenotypes_urls, namespace="phenotypes")),
    url(r"^conditions/", include(conditions_urls, namespace="conditions")),
    url(r"^screens/", include(datasets_urls, namespace="datasets")),
    url(r"^genes/", include(gene_urls, namespace="genes")),
    url(
        r"^robots\.txt?/$",
        TemplateView.as_view(
            template_name="base/robots.txt", content_type="text/plain"
        ),
    ),
    path("sitemap.xml", views.index, {'sitemaps': sitemaps}, name='django.contrib.sitemaps.views.index'),
    path("sitemap-<section>.xml", views.sitemap, {'sitemaps': sitemaps}, name='django.contrib.sitemaps.views.sitemap'),
]
