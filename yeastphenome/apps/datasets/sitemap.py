from django.contrib.sitemaps import Sitemap
from yeastphenome.apps.datasets.models import Dataset


class DatasetSitemap(Sitemap):
    changefreq = "never"
    priority = 0.5

    def items(self):
        return Dataset.objects.all_valid()

    def lastmod(self, obj):
        return obj.data_modified_on
