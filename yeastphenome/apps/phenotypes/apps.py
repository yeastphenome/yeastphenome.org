from __future__ import unicode_literals

from django.apps import AppConfig


class PhenotypesConfig(AppConfig):
    name = "yeastphenome.apps.phenotypes"
    default = True

    def ready(self):
        import yeastphenome.apps.phenotypes.signals
