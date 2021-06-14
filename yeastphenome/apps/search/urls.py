from django.conf.urls import url
from django.urls import path

from yeastphenome.apps.search import views

urlpatterns = [
    url(r"^$", views.index2, name="search"),
]

