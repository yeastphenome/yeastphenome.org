from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

from yeastphenome.apps.phenotypes.models import Observable, Phenotype


@receiver(post_save, sender=Observable)
def update_index_observable(sender, instance, created, **kwargs):
    if instance.is_valid():
        if created:
            instance.update_indexing(mode="create")
        else:
            instance.update_indexing(mode="update")
    else:
        instance.update_indexing(mode="delete")


@receiver(post_delete, sender=Observable)
def delete_index_observable(sender, instance, **kwargs):
    instance.update_indexing(mode="delete")


@receiver(post_save, sender=Phenotype)
@receiver(post_delete, sender=Phenotype)
def update_index_phenotype(sender, instance, created, **kwargs):
    update_index_observable(Observable, instance.observable, False)
