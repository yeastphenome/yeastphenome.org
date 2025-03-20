from django.contrib.sitemaps import Sitemap
from django.urls import reverse


class CommonSitemap(Sitemap):
    priority = 1.0
    changefreq = 'never'

    def items(self):
        return ['common:support',
                'common:about',
                'common:project',
                'common:stats',
                'common:faq',
                'common:contributors',
                'common:data_contributors']

    def location(self, item):
        return reverse(item)
