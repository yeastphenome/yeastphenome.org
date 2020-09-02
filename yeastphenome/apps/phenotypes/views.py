from django.core.paginator import Paginator
from django.conf import settings
from django.views import generic

from yeastphenome.apps.phenotypes.models import Observable
from yeastphenome.apps.phenotypes.search import get_search_tags


class ObservableIndexView(generic.ListView):
    model = Observable
    template_name = "phenotypes/explorer.html"
    context_object_name = "observables"

    def get_context_data(self, **kwargs):
        context = super(ObservableIndexView, self).get_context_data(**kwargs)
        queryset = Observable.objects.order_by("name").all()

        # 50 results per page
        paginator = Paginator(queryset, 50)
        page = self.request.GET.get("page")
        context["observables"] = paginator.get_page(page)
        context["tags"] = get_search_tags()
        return context


class ObservableDetailView(generic.DetailView):
    model = Observable
    template_name = "phenotypes/detail.html"

    def get_context_data(self, **kwargs):
        context = super(ObservableDetailView, self).get_context_data(**kwargs)
        context["DOWNLOAD_PREFIX"] = settings.DOWNLOAD_PREFIX
        context["USER_AUTH"] = self.request.user.is_authenticated
        context["datasets"] = context["object"].datasets
        context["id"] = context["object"].id
        return context
