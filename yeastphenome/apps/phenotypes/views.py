from django.views import generic
from django.conf import settings

from yeastphenome.apps.phenotypes.models import Observable

from ratelimit.mixins import RatelimitMixin
from yeastphenome.settings import (
    VIEW_RATE_LIMIT as rl_rate,
    VIEW_RATE_LIMIT_BLOCK as rl_block,
)


class ObservableIndexView(generic.ListView, RatelimitMixin):
    model = Observable
    template_name = "phenotypes/index.html"
    context_object_name = "observables"
    queryset = Observable.objects.order_by("name").all()
    ratelimit_key = "ip"
    ratelimit_rate = rl_rate
    ratelimit_block = rl_block


class ObservableDetailView(generic.DetailView, RatelimitMixin):
    model = Observable
    template_name = "phenotypes/detail.html"
    ratelimit_key = "ip"
    ratelimit_rate = rl_rate
    ratelimit_block = rl_block

    def get_context_data(self, **kwargs):
        context = super(ObservableDetailView, self).get_context_data(**kwargs)
        context["DOWNLOAD_PREFIX"] = settings.DOWNLOAD_PREFIX
        context["USER_AUTH"] = self.request.user.is_authenticated()
        context["datasets"] = context["object"].datasets
        context["id"] = context["object"].id
        return context
