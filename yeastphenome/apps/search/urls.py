from django.conf.urls import url
from django.urls import path

from yeastphenome.apps.search import views
from yeastphenome.apps.search import cron

urlpatterns = [
    url(r"^$", views.index, name="search"),
    url(r"^update/$", cron.update, name="update"),
    path("update/<str:engines>/", cron.update, name="update"),
]

app_name = "search"
