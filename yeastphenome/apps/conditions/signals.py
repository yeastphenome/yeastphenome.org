from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

from yeastphenome.apps.conditions.models import ConditionType, Condition, ConditionSet


@receiver(post_save, sender=ConditionType)
def update_index_conditiontype(sender, instance, created, **kwargs):
    if instance.is_valid():
        if created:
            instance.update_indexing(mode="create")
        else:
            instance.update_indexing(mode="update")
    else:
        instance.update_indexing(mode="delete")


@receiver(post_delete, sender=ConditionType)
def delete_index_conditiontype(sender, instance, **kwargs):
    instance.update_indexing(mode="delete")


@receiver(post_save, sender=Condition)
@receiver(post_delete, sender=Condition)
def update_index_condition(sender, instance, created=False, **kwargs):
    update_index_conditiontype(ConditionType, instance.type, created)


@receiver(post_save, sender=ConditionSet)
@receiver(post_delete, sender=ConditionSet)
def update_index_conditionset(sender, instance, created=False, **kwargs):
    for condition in instance.conditions.all():
        update_index_condition(Condition, condition, False)
