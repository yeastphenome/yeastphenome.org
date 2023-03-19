from django.contrib.sitemaps import Sitemap
from yeastphenome.apps.phenotypes.models import Observable


class ObservableSitemap(Sitemap):
    changefreq = "never"
    priority = 0.5

    def items(self):
        return Observable.objects.all_valid()
