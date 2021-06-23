from __future__ import unicode_literals

from django.apps import AppConfig


class PapersConfig(AppConfig):
    name = "yeastphenome.apps.papers"
    default = True

    def ready(self):
        import yeastphenome.apps.papers.signals
