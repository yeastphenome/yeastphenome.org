from django.conf.urls import url
from . import views

urlpatterns = [
    url(r"^$", views.index, name="index"),
    url(r"^(?P<pk>\d+)/$", views.ConditiontypeDetailView.as_view(), name="detail"),
    url(r"^chebi/(?P<class_id>\d+)/$", views.conditionclass, name="class"),
    url(r"^tag/(?P<tag_id>\d+)/$", views.conditions_by_tag, name="tag"),
    url(
        r"^media/(?P<pk>\d+)/$", views.MediumDetailView.as_view(), name="medium_detail"
    ),
    url(
        r"^conditionset/(?P<pk>\d+)/$",
        views.ConditionSetDetailView.as_view(),
        name="conditionset_detail",
    ),
]

app_name = "conditions"
