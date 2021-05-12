from __future__ import unicode_literals

from django.core.exceptions import FieldError
from django.db.models import Q
from django.db import models
from django.apps import apps
from django.contrib.humanize.templatetags.humanize import intcomma
from django.urls import reverse
from django.utils.safestring import mark_safe

from yeastphenome.apps.tags.models import Tag


class Collection(models.Model):
    name = models.CharField(max_length=200, null=True, blank=True)
    shortname = models.CharField(max_length=200, null=True, blank=True)
    matingtype = models.CharField(max_length=200, null=True, blank=True)
    ploidy = models.IntegerField(null=True, blank=True)
    description = models.TextField(null=True, blank=True)

    @classmethod
    def all_valid(cls):
        return cls.objects.exclude(
            dataset__paper__latest_data_status__status__name="not relevant"
        )

    def __str__(self):
        return "%s" % self.shortname


class Sourcetype(models.Model):
    name = models.CharField(max_length=200, null=True, blank=True)
    shortname = models.CharField(max_length=200, null=True, blank=True)

    @classmethod
    def all_valid(cls):
        return cls.objects.all()

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
    link = models.TextField(max_length=200, null=True, blank=True)
    person = models.CharField(max_length=200, null=True, blank=True)
    date = models.DateField(null=True)
    acknowledge = models.NullBooleanField()
    release = models.NullBooleanField()

    def __str__(self):
        if self.person:
            return "%s" % self.person
        else:
            return "%s" % self.sourcetype

    @classmethod
    def all_valid(cls):
        return cls.objects.filter(data_source__isnull=False).exclude(
            data_source__paper__latest_data_status__status__name="not relevant"
        )

    def html(self):
        source_str = ""
        if self.person:
            source_str = "%s" % self.person
        else:
            if self.link:
                source_str = '<a class="external" href="%s">%s</a>' % (
                    self.link,
                    self.sourcetype,
                )
            else:
                source_str = "%s" % self.sourcetype
        return mark_safe(source_str)

    def link_or_person(self):
        if self.person:
            return "%s" % self.person
        else:
            if self.link:
                return "%s..." % self.link[: min(60, len(self.link))]
            else:
                return "unknown"

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

    @classmethod
    def all_valid(cls):
        return cls.objects.all()

    def __str__(self):
        return "%s" % self.name


class Dataset(models.Model):

    name = models.CharField(max_length=500, null=True, blank=True, unique=True)
    paper = models.ForeignKey("papers.Paper", on_delete=models.DO_NOTHING)

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

    @property
    def short_name(self):
        """Break the dataset name into words, and return the first 16. If the
        dataset name is longer than that, return those first 8 plus ... then
        the last 8.
        """
        words = self.name.split(" ")
        if len(words) <= 16:
            return " ".join(words)
        return " ".join(words[0:8]) + " ... " + " ".join(words[-8:])

    def __str__(self):
        return "%s" % self.name

    def get_absolute_url(self):
        return reverse("datasets:detail", args=[self.id])

    @classmethod
    def all_valid(cls):
        return cls.objects.exclude(
            Q(paper__latest_data_status__status__name__exact="not relevant")
        ).distinct()

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

    def tested_genes_published(self):
        return self.tested_list_published

    tested_genes_published.boolean = True

    def tested_genes_available(self):
        return self.tested_source is not None

    tested_genes_available.boolean = True

    def tested_space(self):
        if self.tested_source and self.data_set.exists():
            tested_space = intcomma(self.data_set.count())
        elif self.tested_num and self.tested_num > 0:
            tested_space = (
                '<abbr title="The list of tested mutants is not available. '
                "This is an approximate number of tested mutants "
                'as reported by the authors.">~%s</abbr>' % intcomma(self.tested_num)
            )
        else:
            tested_space = "N/A"
        return mark_safe(tested_space)

    def phenotypes(self):
        return self.observable.name

    def tags_link_list(self):
        return mark_safe(", ".join([t.link_detail() for t in self.tags.all()]))

    def has_data_in_db(self):
        return self.data_set.exists()

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

    def get_data(self, reverse=False):
        """Given a dataset, get a sorted list of scores."""
        queryset = (
            Data.objects.filter(dataset=self)
            .filter(valuez__isnull=False)
            .order_by("-valuez")
        )

        if reverse:
            queryset = queryset.reverse()

        return queryset

    def get_ranked_similar(self, reverse=False):
        """Given a dataset, get a sorted listed of similar datasets.
        Assume each pair of datasets is represented twice (A-B and B-A).
        """
        queryset = (
            DatasetSimilarity.objects.filter(dataset1=self)
            .filter(dataset2__data_source__release=True)
            .order_by("-score")
        )

        if reverse:
            queryset = queryset.reverse()

        return queryset


class DatasetSimilarity(models.Model):
    """A dataset similarity is a similarity metric calculated to compare datasets
    based on genes.
    """

    dataset1 = models.ForeignKey(
        Dataset, on_delete=models.CASCADE, related_name="dataset_similarity1"
    )
    dataset2 = models.ForeignKey(
        Dataset, on_delete=models.CASCADE, related_name="dataset_similarity2"
    )
    score = models.DecimalField(max_digits=10, decimal_places=3)

    # IMPORTANT: this is actually a standard deviation
    pvalue = models.DecimalField(max_digits=10, decimal_places=6)

    @classmethod
    def all_valid(cls):
        return cls.objects.exclude(score__isnull=True)

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
        "genes.Gene", null=True, blank=True, on_delete=models.DO_NOTHING
    )
    dataset = models.ForeignKey(Dataset, on_delete=models.DO_NOTHING)

    # Raw phenotypic score
    value = models.DecimalField(max_digits=20, decimal_places=10)

    # Normalized phenotypic score
    valuez = models.DecimalField(max_digits=10, decimal_places=5)

    @classmethod
    def all_valid(cls):
        return cls.objects.exclude(valuez__isnull=True)

    def __str__(self):
        return "%s - %d" % (self.gene.systematic_name, self.dataset.id)
