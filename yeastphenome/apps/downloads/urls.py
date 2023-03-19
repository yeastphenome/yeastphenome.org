from django.urls import path

from . import views

urlpatterns = [
    path("", views.download_bundles, name="download_bundles"),
]

app_name = "downloads"
