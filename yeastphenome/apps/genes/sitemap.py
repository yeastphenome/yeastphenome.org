from django.contrib.sitemaps import Sitemap
from yeastphenome.apps.genes.models import Gene


class GeneSitemap(Sitemap):
    changefreq = "never"
    priority = 0.5

    def items(self):
        return Gene.objects.all_valid()

