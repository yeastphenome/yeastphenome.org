from __future__ import unicode_literals

from django.core.exceptions import FieldError
from django.db.models import F, Q
from django.db import models
from django.apps import apps
from django.contrib.humanize.templatetags.humanize import intcomma
from django.urls import reverse
from django.utils.safestring import mark_safe

from yeastphenome.apps.tags.models import Tag

from yeastphenome.settings import ELASTICSEARCH_HOST, ELASTICSEARCH_AUTH

from elastic_enterprise_search import AppSearch

import itertools


class CollectionManager(models.Manager):
    def all_valid(self):
        # Valid = associated with at least 1 dataset from a relevant paper
        valid_datasets = Dataset.objects.all_valid()
        return self.filter(dataset__in=valid_datasets)


class Collection(models.Model):
    name = models.CharField(max_length=200, null=True, blank=True)
    shortname = models.CharField(max_length=200, null=True, blank=True)
    matingtype = models.CharField(max_length=200, null=True, blank=True)
    ploidy = models.IntegerField(null=True, blank=True)
    description = models.TextField(null=True, blank=True)
    is_valid = models.BooleanField()

    objects = CollectionManager()

    def __str__(self):
        return "%s" % self.shortname


class Sourcetype(models.Model):
    name = models.CharField(max_length=200, null=True, blank=True)
    shortname = models.CharField(max_length=200, null=True, blank=True)

    def __str__(self):
        return "%s" % self.name


class SourceManager(models.Manager):
    def all_valid(self):
        valid_datasets = apps.get_model("datasets", "Dataset").objects.all_valid()
        return (
            self.filter(
                Q(data_source__in=valid_datasets) | Q(tested_source__in=valid_datasets)
            )
            .order_by()
            .distinct()
        )

    def people_to_acknowledge(self):
        valid_datasets = apps.get_model("datasets", "Dataset").objects.all_valid()
        sources = self.filter(sourcetype_id=5).filter(acknowledge=True)
        sources = (
            sources.filter(
                Q(data_source__in=valid_datasets) | Q(tested_source__in=valid_datasets)
            )
            .order_by()
            .distinct()
        )
        people_list = sources.values_list("label", flat=True)
        people_list = [
            person for person in people_list if not person == "" and person is not None
        ]
        people_list = [person.split(", ") for person in people_list]
        people_list = list(set(itertools.chain.from_iterable(people_list)))
        return people_list


class Source(models.Model):
    sourcetype = models.ForeignKey(
        Sourcetype,
        null=True,
        blank=True,
        related_name="sourcetype",
        on_delete=models.DO_NOTHING,
    )
    # link = models.TextField(max_length=200, null=True, blank=True)
    # person = models.CharField(max_length=200, null=True, blank=True)
    label = models.CharField(max_length=200, null=True, blank=True)
    url = models.TextField(null=True, blank=True)
    date = models.DateField(null=True)
    acknowledge = models.NullBooleanField()
    release = models.NullBooleanField()

    objects = SourceManager()

    def __str__(self):
        if self.label:
            return "%s" % self.label
        else:
            return "%s" % self.sourcetype

    def html(self):
        if self.url:
            if self.label:
                source_str = '<a class="external" href="%s">%s</a>' % (
                    self.url,
                    self.label,
                )
            else:
                source_str = '<a class="external" href="%s">%s</a>' % (
                    self.url,
                    self.sourcetype,
                )
        else:
            if self.label:
                source_str = self.label
            else:
                source_str = self.sourcetype
        return mark_safe(source_str)

    def papers(self):
        return (
            apps.get_model("papers", "Paper")
            .objects.filter(dataset__tested_source=self)
            .distinct()
        )

    def papers_str_list(self):
        return ", ".join([("%s" % p) for p in self.papers()])


class Datatype(models.Model):
    name = models.CharField(max_length=200, null=True, blank=True)
    shortname = models.CharField(max_length=20, null=True, blank=True)
    rank = models.PositiveIntegerField(blank=True, null=True)

    def __str__(self):
        return "%s" % self.name


class DatasetManager(models.Manager):
    def all_valid(self):
        datasets = self.filter(paper__latest_data_status__status__is_valid=True)
        datasets = datasets.filter(collection__is_valid=True)
        return datasets

    def all_loaded(self):
        datasets = self.all_valid()
        f = Q(paper__latest_data_status__status__name__exact="loaded") & Q(
            paper__latest_tested_status__status__name__in=[
                "loaded",
                "request abandoned",
                "not available",
            ]
        )
        datasets = datasets.filter(f)
        return datasets


class Dataset(models.Model):

    name = models.CharField(max_length=500, null=True, blank=True, unique=True)
    paper = models.ForeignKey(
        "papers.Paper", related_name="datasets", on_delete=models.DO_NOTHING
    )

    conditionset = models.ForeignKey(
        "conditions.ConditionSet", null=True, blank=True, on_delete=models.DO_NOTHING
    )
    medium = models.ForeignKey(
        "conditions.Medium", null=True, blank=True, on_delete=models.DO_NOTHING
    )

    control_conditionset = models.ForeignKey(
        "conditions.ConditionSet",
        related_name="control_conditionset",
        null=True,
        blank=True,
        on_delete=models.DO_NOTHING,
    )
    control_medium = models.ForeignKey(
        "conditions.Medium",
        related_name="control_medium",
        null=True,
        blank=True,
        on_delete=models.DO_NOTHING,
    )

    phenotype = models.ForeignKey(
        "phenotypes.Phenotype", null=True, blank=True, on_delete=models.DO_NOTHING
    )
    collection = models.ForeignKey(
        Collection, null=True, blank=True, on_delete=models.DO_NOTHING
    )

    notes = models.TextField(null=True, blank=True)

    tested_num = models.IntegerField(default=0, null=True)
    tested_list_published = models.NullBooleanField()
    tested_source = models.ForeignKey(
        Source,
        null=True,
        blank=True,
        related_name="tested_source",
        on_delete=models.DO_NOTHING,
    )

    data_source = models.ForeignKey(
        Source,
        null=True,
        blank=True,
        related_name="data_source",
        on_delete=models.DO_NOTHING,
    )

    data_measured = models.ForeignKey(
        Datatype,
        null=True,
        blank=True,
        related_name="data_measured",
        on_delete=models.DO_NOTHING,
    )
    data_published = models.ForeignKey(
        Datatype,
        null=True,
        blank=True,
        related_name="data_published",
        on_delete=models.DO_NOTHING,
    )
    data_available = models.ForeignKey(
        Datatype,
        null=True,
        blank=True,
        related_name="data_available",
        on_delete=models.DO_NOTHING,
    )

    tags = models.ManyToManyField(Tag, blank=True)
    data_modified_on = models.DateField(null=True, blank=True)

    objects = DatasetManager()

    def __str__(self):
        return "%s" % self.name

    def is_valid(self):
        cond1 = (
            self.paper.latest_data_status.status.is_valid
            if self.paper.latest_data_status.status.is_valid
            else False
        )
        cond2 = False
        if self.collection:
            cond2 = self.collection.is_valid if self.collection.is_valid else False
        return cond1 & cond2

    # Necessary to run database-wide updates of dataset names
    def save(self, *args, **kwargs):
        self.name = "%s | %s | %s | %s | %s" % (
            self.collection,
            self.phenotype,
            self.conditionset,
            self.medium,
            self.paper,
        )
        super(Dataset, self).save(*args, **kwargs)

    def admin_name(self):
        dm = "na"
        if self.data_measured_id is not None:
            dm = self.data_measured.shortname
        dp = "na"
        if self.data_published_id is not None:
            dp = self.data_published.shortname
        da = "na"
        if self.data_available_id is not None:
            da = self.data_available.shortname
        data_info = [dm, dp, da]
        data_all = "%s | %s" % (self.name, ", ".join(data_info))
        return data_all

    class Meta:
        ordering = ["id"]

    def get_data_availability(self):
        availability = {}
        num_available_data = self.data.count()
        availability["type_data_available"] = self.data_available

        if self.tested_source:
            availability["tested_available"] = mark_safe(
                "%s (%s mutants)"
                % (self.tested_source.html(), intcomma(num_available_data))
            )
        else:
            availability["tested_available"] = "no"

        if self.data_source:
            availability["data_available"] = mark_safe(
                "%s (%s mutants)"
                % (self.data_source.html(), intcomma(num_available_data))
            )
        else:
            availability["data_available"] = "%s mutants" % num_available_data

        return availability

    def tested_genes_published(self):
        return self.tested_list_published

    tested_genes_published.boolean = True

    def tested_genes_available(self):
        return self.tested_source is not None

    tested_genes_available.boolean = True

    def tested_space(self):
        if self.tested_source and self.data.exists():
            tested_space = intcomma(self.data.count())
        elif self.tested_num and self.tested_num > 0:
            tested_space = (
                '<abbr title="The list of tested mutants is not available. '
                "This is an approximate number of tested mutants "
                'as reported by the authors.">~%s</abbr>' % intcomma(self.tested_num)
            )
        else:
            tested_space = "N/A"
        return mark_safe(tested_space)

    def phenotype_aliases_list(self):
        aliases = self.phenotype.aliases_list() if self.phenotype else []
        return aliases

    def phenotype_aliases_list_as_str(self):
        return "; ".join(self.phenotype_aliases_list())

    def conditions_aliases_list(self):
        conditionset_aliases = (
            self.conditionset.aliases_list() if self.conditionset else []
        )
        medium_aliases = [str(self.medium)] if self.medium else []
        aliases = list(set(conditionset_aliases + medium_aliases))
        return aliases

    def conditions_aliases_list_as_str(self):
        return "; ".join(self.conditions_aliases_list())

    def tags_list(self):
        tags_list_self = list(self.tags.values_list("name", flat=True))
        tags_list_phenotype = self.phenotype.tags_list() if self.phenotype else []
        tags_list_conditionset = (
            self.conditionset.tags_list() if self.conditionset else []
        )
        tags_list = list(
            set(tags_list_self + tags_list_phenotype + tags_list_conditionset)
        )
        return tags_list

    def tags_list_as_str(self):
        return "; ".join(self.tags_list())

    def tags_list_as_links(self):
        return mark_safe("; ".join([t.link_detail() for t in self.tags.all()]))

    def has_data_in_db(self):
        return self.data.exists()

    has_data_in_db.boolean = True

    def link_edit(self):
        style = ""
        if self.paper.latest_data_status and (
            self.paper.latest_data_status.status_id == 10
        ):  # paper not relevant
            style = ' style="color: gray;"'
        html = '<a href="%s" %s>%s</a>' % (
            reverse("admin:datasets_dataset_change", args=(self.id,)),
            style,
            self,
        )
        return mark_safe(html)

    def get_scores(self):
        data = self.data.filter(valuez__isnull=False).values(
            "valuez",
            "gene_id",
            gene_systematic_name=F("gene__systematic_name"),
            gene_common_name=F("gene__common_name"),
        )
        return data

    def get_similarities(self):
        data = self.similarities.filter(dataset2__data_source__release=True)
        data = data.filter(~Q(dataset2__collection__shortname="het"))
        data = data.values(
            "score", "pvalue", "dataset2_id", dataset2_name=F("dataset2__name")
        )
        return data

    def indexing_progress(self):
        print(self.id)

    def data_indexing(self):
        json = {
            "id": self.id,
            "paper": self.paper.systematic_name if self.paper else "",
            "collection": self.collection.shortname if self.collection else "",
            "data_available": self.data_available.shortname
            if self.data_available
            else "",
            "medium": self.medium.display_name if self.medium else "",
            "conditionset": self.conditionset.display_name if self.conditionset else "",
            "conditions_aliases_list_as_str": self.conditions_aliases_list_as_str(),
            "phenotype": self.phenotype.name if self.phenotype else "",
            "phenotype_aliases_list_as_str": self.phenotype_aliases_list_as_str(),
            "tags_list_as_str": self.tags_list_as_str(),
        }
        return json

    def update_indexing(self, mode="create"):

        app_search = AppSearch(
            ELASTICSEARCH_HOST,
            http_auth=ELASTICSEARCH_AUTH,
        )

        if mode == "update":
            _ = app_search.put_documents(
                engine_name="datasets", documents=[self.data_indexing()]
            )
        elif mode == "delete":
            _ = app_search.delete_documents(
                engine_name="datasets", document_ids=[self.id]
            )
        elif mode == "create":
            _ = app_search.index_documents(
                engine_name="datasets", documents=[self.data_indexing()]
            )

        # Update related indices
        if self.conditionset:
            conditions = self.conditionset.conditions.all()
            documents = [condition.type.data_indexing() for condition in conditions]
            _ = app_search.put_documents(
                engine_name="conditiontypes", documents=documents
            )
        if self.phenotype:
            observable = self.phenotype.observable
            _ = app_search.put_documents(
                engine_name="observables", documents=[observable.data_indexing()]
            )
        if self.paper:
            paper = self.paper
            _ = app_search.put_documents(
                engine_name="papers", documents=[paper.data_indexing()]
            )


class DatasetSimilarity(models.Model):
    """A dataset similarity is a similarity metric calculated to compare datasets
    based on genes.
    """

    dataset1 = models.ForeignKey(
        Dataset, on_delete=models.CASCADE, related_name="similarities"
    )
    dataset2 = models.ForeignKey(
        Dataset, on_delete=models.CASCADE, related_name="dataset_similarity2"
    )
    score = models.DecimalField(max_digits=10, decimal_places=3)

    # IMPORTANT: this is actually a standard deviation
    pvalue = models.DecimalField(max_digits=10, decimal_places=6)

    def save(self, *args, **kwargs):
        """Override the save function to ensure that only one similarity score
        for any pair of datasets can be created. If a different ordering is
        presented, it is fixed and we get an integrity error.
        """
        # Only update order if not in databsase yet, ensure ordered by name
        if not self.pk:

            if self.score in [None, "", "nan"]:
                raise FieldError(
                    "score for a gene similarity cannot be a null or empty value."
                )

        super(DatasetSimilarity, self).save(*args, **kwargs)

    class Meta:
        unique_together = (
            "dataset1",
            "dataset2",
        )


class DataManager(models.Manager):
    def all_valid(self):
        valid_datasets = Dataset.objects.all_valid()
        return self.filter(dataset__in=valid_datasets)


class Data(models.Model):

    gene = models.ForeignKey(
        "genes.Gene",
        null=True,
        blank=True,
        related_name="data",
        on_delete=models.DO_NOTHING,
    )
    dataset = models.ForeignKey(
        Dataset, related_name="data", on_delete=models.DO_NOTHING
    )

    # Raw phenotypic score
    value = models.DecimalField(max_digits=20, decimal_places=10)

    # Normalized phenotypic score
    valuez = models.DecimalField(max_digits=10, decimal_places=5)

    objects = DataManager()

    def __str__(self):
        return "%s - %d" % (self.gene.systematic_name, self.dataset.id)
