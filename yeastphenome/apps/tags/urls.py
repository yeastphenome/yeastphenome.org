from django.conf.urls import url
from . import views

# urlpatterns = [
#     url(r"^$", views.index, name="index"),
#     url(r"^tag/$", views.redirect_index, name="redirect_index"),
#     url(r"^tag/(?P<tag_id>\d+)$", views.phenotypes_by_tag, name="tag"),
#     url(r"^tag/(?P<phenotype_id>\d+)/all$", views.phenotypes_by_tags, name="tags"),
#     url(r"^(?P<pk>\d+)/$", views.ObservableDetailView.as_view(), name="detail"),
# ]

app_name = "tags"
