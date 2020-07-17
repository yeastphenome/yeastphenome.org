from django.conf.urls import include, url

from yeastphenome.apps import papers
from yeastphenome.apps.papers import urls as papers_urls
from yeastphenome.apps.common import urls as common_urls
from yeastphenome.apps.phenotypes import urls as phenotypes_urls
from yeastphenome.apps.conditions import urls as conditions_urls
from yeastphenome.apps.datasets import urls as datasets_urls

from django.contrib import admin
admin.autodiscover()

urlpatterns = [
    url(r'^admin/', admin.site.urls),
    url(r'^', include(common_urls)),
    url(r'^papers/', include(papers_urls, namespace="papers")),
    url(r'^phenotypes/', include(phenotypes_urls, namespace="phenotypes")),
    url(r'^conditions/', include(conditions_urls, namespace="conditions")),
    url(r'^datasets/', include(datasets_urls, namespace="datasets")),

    # This one papers view should not be nested under papers/ prefix
    url(r'^contributors/', papers.views.ContributorsListView.as_view(), name="contributors")
]
