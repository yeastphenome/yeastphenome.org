from django_elasticsearch_dsl import Document, fields
from django_elasticsearch_dsl.registries import registry

from yeastphenome.apps.genes.models import Gene


@registry.register_document
class GeneDocument(Document):

    class Index:
        name = 'genes'
        settings = {'number_of_shards': 1,
                    'number_of_replicas': 0}

    class Django:
        model = Gene

    id = fields.IntegerField(attr="id")
    systematic_name = fields.TextField(attr="systematic_name",
                                       fields={"raw": fields.KeywordField()})
    common_name = fields.TextField(attr="common_name",
                                   fields={"raw": fields.KeywordField()})
    description = fields.TextField(attr="description")

    aliases = fields.ObjectField(
        attr='aliases_indexing',
        properties={
            'list_as_str_txt': fields.TextField(),
            'list_as_str_kwd': fields.KeywordField(),
        },
    )

    def get_queryset(self):
        return Gene.objects.all_valid()

    # Optional: to ensure the Paper will be re-saved when Tags is updated
    # related_models = [Tag]

    # def get_instances_from_related(self, related_instance):
    #     """If related_models is set, define how to retrieve the Car instance(s) from the related model.
    #     The related_models option should be used with caution because it can lead in the index
    #     to the updating of a lot of items.
    #     """
    #     if isinstance(related_instance, Tag):
    #         return related_instance.paper_set.all()
    #     else:
    #         pass


    # Ignore auto updating of Elasticsearch when a model is saved
    # or deleted:
    # ignore_signals = True

    # Don't perform an index refresh after every update (overrides global setting):
    # auto_refresh = False

    # Paginate the django queryset used to populate the index with the specified size
    # (by default it uses the database driver's default setting)
    # queryset_pagination = 5000