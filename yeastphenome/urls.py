from django.conf.urls import include, url

from yeastphenome.apps import papers

from django.contrib import admin
admin.autodiscover()

urlpatterns = [
    url(r'^admin/', include(admin.site.urls)),
    url(r'^', include('common.urls', namespace="common")),
    url(r'^papers/', include('papers.urls', namespace="papers")),
    url(r'^phenotypes/', include('phenotypes.urls', namespace="phenotypes")),
    url(r'^conditions/', include('conditions.urls', namespace="conditions")),
    url(r'^datasets/', include('datasets.urls', namespace="datasets")),

    # This one papers view should not be nested under papers/ prefix
    url(r'^contributors/', papers.views.ContributorsListView.as_view(), name="contributors")
]
