from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

from elastic_enterprise_search import AppSearch

from yeastphenome.apps.papers.models import Paper
from yeastphenome.settings import (
    ELASTICSEARCH_HOST,
    ELASTICSEARCH_AUTH
)

@receiver(post_save, sender=Paper)
def update_index(sender, instance, created, **kwargs):
    if instance.is_valid():

        app_search = AppSearch(
            ELASTICSEARCH_HOST,
            http_auth=ELASTICSEARCH_AUTH,
        )

        resp = app_search.get_documents(
            engine_name="papers",
            document_ids=[instance.id]
        )

        if not resp[0]:
            instance.update_indexing(mode="create")
        else:
            instance.update_indexing(mode="update")

    else:
        instance.update_indexing(mode="delete")


@receiver(post_delete, sender=Paper)
def delete_index(sender, instance, **kwargs):
    instance.update_indexing(mode="delete")
