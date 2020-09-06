from __future__ import unicode_literals

from django.core.exceptions import FieldError
from django.db.models import Q
from django.db import models
from django.apps import apps
from django.contrib.humanize.templatetags.humanize import intcomma
from django.urls import reverse


class Collection(models.Model):
    name = models.CharField(max_length=200, null=True, blank=True)
    shortname = models.CharField(max_length=200, null=True, blank=True)
    matingtype = models.CharField(max_length=200, null=True, blank=True)
    ploidy = models.IntegerField(null=True, blank=True)
    description = models.TextField(null=True, blank=True)

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

    def html(self):
        if self.person:
            return "%s" % self.person
        else:
            if self.link:
                return '<a class="external" href="%s">%s</a>' % (
                    self.link,
                    self.sourcetype,
                )
            else:
                return "%s" % self.sourcetype

    html.allow_tags = True

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

    def __str__(self):
        return "%s" % self.name


class Tag(models.Model):
    name = models.CharField(max_length=200, null=True, blank=True)
    description = models.TextField(max_length=1000, null=True, blank=True)

    def __str__(self):
        s = ""
        if self.name:
            s = self.name
        return s

    def link_detail(self):
        return '<a href="%s">%s</a>' % (reverse("datasets:tag", args=(self.id,)), self)

    link_detail.allow_tags = True

    def datasets(self):
        return (
            apps.get_model("datasets", "Dataset")
            .objects.filter(tags=self)
            .exclude(paper__latest_data_status__status__name="not relevant")
            .order_by("name")
            .all()
        )

    def datasets_number(self):
        return self.datasets().count()

    def datasets_edit_link_list(self):
        s = "<ul>"
        s = s + "<li>".join([d.link_edit() for d in self.datasets()])
        s = s + "</ul>"
        return s

    datasets_edit_link_list.allow_tags = True


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

    def __str__(self):
        return "%s" % self.name

    def get_absolute_url(self):
        return reverse("datasets:detail", args=[self.id])

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
        return tested_space

    tested_space.allow_tags = True

    def phenotypes(self):
        return self.observable.name

    def tags_link_list(self):
        return ", ".join([t.link_detail() for t in self.tags.all()])

    tags_link_list.allow_tags = True

    def has_data_in_db(self):
        return self.data_set.exists()

    has_data_in_db.boolean = True

    def link_edit(self):
        html = '<a href="%s">%s</a>' % (
            reverse("admin:datasets_dataset_change", args=(self.id,)),
            self,
        )
        return html

    link_edit.allow_tags = True


class GeneAlias(models.Model):
    """A GeneAlias is another name for a gene"""

    name = models.CharField(max_length=250, null=True, blank=True, unique=True)

    def __str__(self):
        return "<%s>" % self.name


class Gene(models.Model):

    # previously data.orf field, corresponds to 4. Feature name, YAL*
    systematic_name = models.CharField(
        max_length=50, null=True, blank=True, unique=True
    )

    # corresponds to 1. Primary SGDID, intended to query SGD API if needed
    primary_sgdid = models.CharField(max_length=50, null=True, blank=True, unique=True)

    # Cooresponds to 5. Standard gene name, if defined
    common_name = models.CharField(max_length=50, null=True, blank=True, unique=True)

    # Corresponds to 6. Alias (optional, multiples separated by |)
    aliases = models.ManyToManyField(GeneAlias, blank=True)

    # TODO: additional mutations resulting from perturbing gene
    # genome_alterations, acquired_secondary_alterations

    def get_ranked_similar(self, reverse=False):
        """Given a gene, get a sorted listed from the most to least similar
        """
        if not reverse:
            return GeneSimilarity.objects.filter(
                Q(gene1=self) | Q(gene2=self)
            ).order_by("-score")
        return GeneSimilarity.objects.filter(Q(gene1=self) | Q(gene2=self)).order_by(
            "score"
        )

    def __str__(self):
        return "<%s>" % self.systematic_name


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
    metric = models.CharField(max_length=50)
    score = models.DecimalField(max_digits=10, decimal_places=3)
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

            # Ensure similarity ordered by systematic name
            if self.dataset1.name > self.dataset2.name:
                holder = self.dataset1
                self.dataset1 = self.dataset2
                self.dataset2 = holder

        super(DatasetSimilarity, self).save(*args, **kwargs)

    class Meta:
        unique_together = (
            "dataset1",
            "dataset2",
            "metric",
        )


class GeneSimilarity(models.Model):
    """A gene similarity is a similarity metric calculated to compare genes
       based on datasets.
    """

    gene1 = models.ForeignKey(
        Gene, on_delete=models.CASCADE, related_name="gene_similarity1"
    )
    gene2 = models.ForeignKey(
        Gene, on_delete=models.CASCADE, related_name="gene_similarity2"
    )
    metric = models.CharField(max_length=50)
    score = models.DecimalField(max_digits=10, decimal_places=3)
    pvalue = models.DecimalField(max_digits=10, decimal_places=6)

    def save(self, *args, **kwargs):
        """Override the save function to ensure that only one similarity score
           for any pair of genes can be created. If a different ordering is 
           presented, it is fixed and we get an integrity error.
        """
        # Only update order if not in databsase yet, ensure genes ordered by name
        if not self.pk:

            if self.score in [None, "", "nan"]:
                raise FieldError(
                    "score for a gene similarity cannot be a null or empty value."
                )

            # Ensure similarity ordered by systematic name
            if self.gene1.systematic_name > self.gene2.systematic_name:
                holder = self.gene1
                self.gene1 = self.gene2
                self.gene2 = holder

        super(GeneSimilarity, self).save(*args, **kwargs)

    class Meta:
        unique_together = (
            "gene1",
            "gene2",
            "metric",
        )


class Data(models.Model):
    dataset = models.ForeignKey(Dataset, on_delete=models.DO_NOTHING)
    value = models.DecimalField(max_digits=10, decimal_places=3)

    # orf can eventually be deleted when the Gene model is migrated in production
    orf = models.CharField(max_length=50)
    gene = models.ForeignKey(
        "datasets.Gene", null=True, blank=True, on_delete=models.DO_NOTHING
    )

    def __str__(self):
        return "%s - %s" % (self.orf, self.value)
