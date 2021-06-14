from django_elasticsearch_dsl import Document, fields
from django_elasticsearch_dsl.registries import registry

from yeastphenome.apps.papers.models import Paper


@registry.register_document
class PaperDocument(Document):

    class Index:
        name = 'papers'
        settings = {'number_of_shards': 1,
                    'number_of_replicas': 0}

    class Django:
        model = Paper
        parallel_indexing = True

    # Try to monitor progress
    progress = fields.KeywordField(attr="indexing_progress")

    # Fields only for display and sorting
    id = fields.IntegerField(attr="id")
    first_author = fields.KeywordField(attr="first_author")
    last_author = fields.KeywordField(attr="last_author")
    systematic_name = fields.TextField(attr="systematic_name",
                                       fields={"raw": fields.KeywordField()})
    pmid = fields.IntegerField(attr="pmid")
    pub_date = fields.DateField(attr="pub_date", format="year")

    # Fields for searching
    phenotypes = fields.ObjectField(
        attr='phenotypes_indexing',
        properties={
            'summary': fields.KeywordField(),                   # for display & sorting
            # 'list_as_str': fields.TextField(),                  # for searching
        },
    )
    conditions = fields.ObjectField(
        attr='conditions_indexing',
        properties={
            'summary': fields.KeywordField(),                   # for display & sorting
            # 'list_as_str': fields.TextField(),                  # for searching
        },
    )
    tags = fields.ObjectField(
        attr='tags_indexing',
        properties={
            'list_as_str': fields.KeywordField(),               # for display & sorting
            # 'list': fields.KeywordField(multi=True),            # for searching (exact match)
        },
    )

    def get_queryset(self):
        return Paper.objects.all_valid()

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