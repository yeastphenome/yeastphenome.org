from __future__ import unicode_literals

from django.apps import AppConfig


class ConditionsConfig(AppConfig):
    name = "yeastphenome.apps.conditions"
    default = True

    def ready(self):
        import yeastphenome.apps.conditions.signals
