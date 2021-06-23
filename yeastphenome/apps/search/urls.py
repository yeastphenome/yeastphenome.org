from django.conf.urls import url

from yeastphenome.apps.search import views
from yeastphenome.apps.search import cron

urlpatterns = [
    url(r"^$", views.index, name="search"),
    url(r"^update/$", cron.update, name="update")
]

