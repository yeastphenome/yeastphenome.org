from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

from yeastphenome.apps.datasets.models import Dataset


@receiver(post_save, sender=Dataset)
def update_index(sender, instance, created, **kwargs):
    if instance.is_valid():
        if created:
            instance.update_indexing(mode="create")
        else:
            instance.update_indexing(mode="update")
    else:
        instance.update_indexing(mode="delete")


@receiver(post_delete, sender=Dataset)
def delete_index(sender, instance, **kwargs):
    instance.update_indexing(mode="delete")
