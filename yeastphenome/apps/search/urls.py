from django.urls import path, re_path

from yeastphenome.apps.search import views
from yeastphenome.apps.search import cron

urlpatterns = [
    re_path(r"^$", views.search_index_view, name="search"),
    # url(r"^update/$", cron.update, name="update"),
    # path("update/<str:engine>/", cron.update, name="update"),
]

app_name = "search"
