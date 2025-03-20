from django.contrib.sitemaps import Sitemap
from yeastphenome.apps.conditions.models import ConditionType


class ConditionTypeSitemap(Sitemap):
    changefreq = "yearly"
    priority = 1.0

    def items(self):
        return ConditionType.objects.all_valid()
