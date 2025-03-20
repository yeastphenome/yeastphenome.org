from django.contrib.sitemaps import Sitemap
from yeastphenome.apps.datasets.models import Dataset


class DatasetSitemap(Sitemap):
    changefreq = "never"
    priority = 1.0

    def items(self):
        return Dataset.objects.all_valid()

