from django.contrib.sitemaps import Sitemap
from yeastphenome.apps.conditions.models import ConditionType


class ConditionTypeSitemap(Sitemap):
    changefreq = "never"
    priority = 0.5

    def items(self):
        return ConditionType.objects.all_valid()
