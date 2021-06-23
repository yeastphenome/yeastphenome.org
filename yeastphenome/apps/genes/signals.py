from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

from yeastphenome.apps.genes.models import Gene


@receiver(post_save, sender=Gene)
def update_index(sender, instance, created, **kwargs):
    if created:
        instance.update_indexing(mode="create")
    else:
        instance.update_indexing(mode="update")


@receiver(post_delete, sender=Gene)
def delete_index(sender, instance, **kwargs):
    instance.update_indexing(mode="delete")
