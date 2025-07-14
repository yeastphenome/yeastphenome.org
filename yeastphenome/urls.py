from django.urls import include, re_path, path
from django.contrib import admin
from django.contrib.sitemaps import views as sitemaps_views
from django.conf import settings

from yeastphenome.apps.papers import urls as papers_urls
from yeastphenome.apps.common import urls as common_urls
from yeastphenome.apps.phenotypes import urls as phenotypes_urls
from yeastphenome.apps.conditions import urls as conditions_urls
from yeastphenome.apps.datasets import urls as datasets_urls
from yeastphenome.apps.genes import urls as gene_urls
from yeastphenome.apps.search import urls as search_urls
from yeastphenome.apps.downloads import urls as downloads_urls
from yeastphenome.apps.updates import urls as updates_urls

from yeastphenome.apps.papers.sitemap import PaperSitemap
from yeastphenome.apps.conditions.sitemap import ConditionTypeSitemap
from yeastphenome.apps.datasets.sitemap import DatasetSitemap
from yeastphenome.apps.genes.sitemap import GeneSitemap
from yeastphenome.apps.phenotypes.sitemap import ObservableSitemap
from yeastphenome.apps.common.sitemap import CommonSitemap

from yeastphenome.apps.common import views

sitemaps = {'papers': PaperSitemap,
            'conditions': ConditionTypeSitemap,
            'datasets': DatasetSitemap,
            'genes': GeneSitemap,
            'phenotypes': ObservableSitemap,
            'common': CommonSitemap}

admin.autodiscover()

urlpatterns = [
    re_path(r"^admin/", admin.site.urls),
    re_path(r"^", include(common_urls, namespace="common")),
    re_path(r"^search/", include(search_urls, namespace="search")),
    re_path(r"^papers/", include(papers_urls, namespace="papers")),
    re_path(r"^phenotypes/", include(phenotypes_urls, namespace="phenotypes")),
    re_path(r"^conditions/", include(conditions_urls, namespace="conditions")),
    re_path(r"^screens/", include(datasets_urls, namespace="datasets")),
    re_path(r"^genes/", include(gene_urls, namespace="genes")),
    re_path(r"^downloads/", include(downloads_urls, namespace="downloads")),
    re_path(r"^updates/", include(updates_urls, namespace="updates")),
    path("sitemap.xml", sitemaps_views.index, {'sitemaps': sitemaps}, name='django.contrib.sitemaps.views.index'),
    path("sitemap-<section>.xml", sitemaps_views.sitemap, {'sitemaps': sitemaps}, name='django.contrib.sitemaps.views.sitemap'),
    path('<path:url>', views.handler404, name='handler404'),
]

if 'robots' in settings.INSTALLED_APPS:
    urlpatterns += [
        re_path(r'^robots\.txt', include('robots.urls')),
    ]
