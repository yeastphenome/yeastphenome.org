from __future__ import unicode_literals

from django.apps import AppConfig
from django.db.models.signals import post_save
from django.dispatch import receiver


class ConditionsConfig(AppConfig):
    name = "yeastphenome.apps.conditions"
    default = True

    def ready(self):
        print("at ready")
        post_save.connect(receiver, sender='conditions.ConditionType')
        # import yeastphenome.apps.conditions.signals
