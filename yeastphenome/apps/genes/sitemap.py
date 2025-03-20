from django.contrib.sitemaps import Sitemap
from yeastphenome.apps.genes.models import Gene


class GeneSitemap(Sitemap):
    changefreq = "yearly"
    priority = 1.0

    def items(self):
        return Gene.objects.all_valid()

