from django.contrib.sitemaps import Sitemap
from yeastphenome.apps.phenotypes.models import Observable


class ObservableSitemap(Sitemap):
    changefreq = "yearly"
    priority = 1.0

    def items(self):
        return Observable.objects.all_valid()
