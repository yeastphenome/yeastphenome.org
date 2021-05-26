from django.urls import path

from . import views

urlpatterns = [
    path("<int:tag_id>/", views.tag_detail, name="detail"),
]

app_name = "tags"
