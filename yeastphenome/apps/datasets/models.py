from __future__ import unicode_literals

from django.core.exceptions import FieldError
from django.db.models import F, Q
from django.db import models
from django.apps import apps
from django.contrib.humanize.templatetags.humanize import intcomma
from django.urls import reverse
from django.utils.safestring import mark_safe

from yeastphenome.apps.tags.models import Tag
from yeastphenome.apps.datasets.managers import CollectionManager, SourceManager, DatasetManager, DataManager


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
    acknowledge = models.BooleanField(null=True, blank=True)
    release = models.BooleanField(null=True, blank=True)

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
    tested_list_published = models.BooleanField(null=True, blank=True)
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

    def get_absolute_url(self):
        return reverse("datasets:detail", args=(self.id,))

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

        availability["tested_available"] = "no"
        if self.tested_source:
            if self.tested_source.release:
                availability["tested_available"] = mark_safe(
                    "%s (%s mutants)"
                    % (self.tested_source.html(), intcomma(num_available_data))
                )

        availability["data_available"] = "%s mutants" % num_available_data
        if self.data_source:
            if self.data_source.release:
                availability["data_available"] = mark_safe(
                    "%s (%s mutants)"
                    % (self.data_source.html(), intcomma(num_available_data))
                )

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
        tags_list_medium = (self.medium.tags_list() if self.medium else [])
        tags_list = list(
            set(tags_list_self + tags_list_phenotype + tags_list_conditionset + tags_list_medium)
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

    def get_similarity_to(self, dataset2):
        data = self.similarities.filter(dataset2=dataset2).first()
        return data


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
