from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

from yeastphenome.apps.conditions.models import ConditionType


@receiver(post_save, sender=ConditionType)
def update_index(sender, instance, created, **kwargs):
    print("yes")
    instance.update_indexing()


@receiver(post_delete, sender=ConditionType)
def delete_index(sender, instance, created, **kwargs):
    instance.delete_indexing()
