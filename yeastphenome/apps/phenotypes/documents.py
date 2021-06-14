from django_elasticsearch_dsl import Document, fields
from django_elasticsearch_dsl.registries import registry

from yeastphenome.apps.phenotypes.models import Observable


@registry.register_document
class ObservableDocument(Document):

    class Index:
        name = 'observables'
        settings = {'number_of_shards': 1,
                    'number_of_replicas': 0}

    class Django:
        model = Observable

    id = fields.IntegerField(attr="id")
    name = fields.TextField(attr="name",
                            fields={"raw": fields.KeywordField()})
    description = fields.TextField(attr="description")

    conditions = fields.KeywordField(attr="conditiontypes_list_as_str")
    papers = fields.KeywordField(attr="papers_list_as_str")

    phenotypes = fields.TextField(attr="phenotypes_list_as_str")

    reporters = fields.ObjectField(
        attr='reporters_indexing',
        properties={
            'list_as_str_txt': fields.TextField(),      # for searching (partial match, case insensitive)
            'list_as_str_kwd': fields.KeywordField(),   # for sorting
        },
    )

    tags = fields.ObjectField(
        attr='tags_indexing',
        properties={
            'list': fields.KeywordField(multi=True),    # for searching (exact match)
            'list_as_str': fields.KeywordField(),       # for sorting
        },
    )

    def get_queryset(self):
        return Observable.objects.all_valid()

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