from django.contrib.sitemaps import Sitemap
from yeastphenome.apps.papers.models import Paper


class PaperSitemap(Sitemap):
    changefreq = "never"
    priority = 0.5

    def items(self):
        return Paper.objects.all_valid()

    def lastmod(self, obj):
        return obj.modified_on