from django.conf.urls import url
from . import views

urlpatterns = [
    url(r"^$", views.index, name="index"),
    # Redirect to conditions search if user navigates to these pages
    url(r"^sets/$", views.redirect_index, name="redirect_index"),
    url(r"^media/$", views.redirect_index, name="redirect_index"),
    url(r"^chebi/$", views.redirect_index, name="redirect_index"),
    url(r"^tags/$", views.tag_browser, name="tags"),
    url(r"^browse/$", views.browse, name="browse"),
    url(r"^(?P<pk>\d+)/$", views.ConditiontypeDetailView.as_view(), name="detail"),
    url(r"^tags/(?P<tag_id>\d+)/$", views.conditions_by_tag, name="tag"),
    url(
        r"^media/(?P<pk>\d+)/$", views.MediumDetailView.as_view(), name="medium_detail"
    ),
    url(
        r"^sets/(?P<pk>\d+)/$",
        views.ConditionSetDetailView.as_view(),
        name="conditionset_detail",
    ),
]

app_name = "conditions"
