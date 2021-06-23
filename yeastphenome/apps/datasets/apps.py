from __future__ import unicode_literals

from django.apps import AppConfig


class DatasetsConfig(AppConfig):
    name = "yeastphenome.apps.datasets"
    default = True

    def ready(self):
        import yeastphenome.apps.datasets.signals