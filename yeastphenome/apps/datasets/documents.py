from django_elasticsearch_dsl import Document, fields
from django_elasticsearch_dsl.registries import registry

from yeastphenome.apps.datasets.models import Dataset


@registry.register_document
class DatasetDocument(Document):

    class Index:
        name = 'datasets'
        settings = {'number_of_shards': 1,
                    'number_of_replicas': 0}

    class Django:
        model = Dataset
        parallel_indexing = True
        queryset_pagination = 1000

    # Fields only for display and sorting
    id = fields.IntegerField(attr='id')
    name = fields.KeywordField(attr='name')
    paper = fields.ObjectField(
        attr='paper',
        properties={
            'systematic_name': fields.KeywordField()
        })
    collection = fields.ObjectField(
        attr="collection",
        properties={
            'shortname': fields.KeywordField()
        })
    data_available = fields.ObjectField(
        attr="data_available",
        properties={
            'name': fields.KeywordField()
        })

    # Fields for searching
    phenotype = fields.ObjectField(
        attr='phenotype_indexing',
        properties={
            'name_as_str': fields.KeywordField(),       # for display & sorting
            'list_as_str': fields.TextField()           # for searching
        })
    conditions = fields.ObjectField(
        attr='conditions_indexing',
        properties={
            'name_as_str': fields.KeywordField(),       # for display & sorting
            'list_as_str': fields.TextField()           # for searching
        })
    medium = fields.ObjectField(
        attr="medium_indexing",
        properties={
            'name_kwd': fields.KeywordField(),          # for display & sorting
            'name_txt': fields.TextField()              # for searching
        })
    tags = fields.ObjectField(
        attr='tags_indexing',
        properties={
            'list_as_str': fields.KeywordField(),       # for display & sorting
            'list': fields.KeywordField(multi=True),    # for searching (exact match)
        },
    )

    # Try to monitor progress
    progress = fields.KeywordField(attr="indexing_progress")

    def get_queryset(self):
        datasets = Dataset.objects.all_valid()
        return datasets.select_related("paper",
                                       "medium",
                                       "collection",
                                       "data_available")


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