from __future__ import unicode_literals

from django.core.exceptions import FieldError
from django.db import models
from django.db.models import F
from django.urls import reverse
from django.utils.safestring import mark_safe

from yeastphenome.apps.datasets.models import Data
from yeastphenome.apps.common.utils_format import update_values_with_percentile


class GeneAlias(models.Model):
    """A GeneAlias is another name for a gene"""

    name = models.CharField(max_length=250, null=False, blank=False, unique=True)

    def __str__(self):
        return "%s" % self.name


class GeneManager(models.Manager):

    def all_valid(self):
        return self.all()


class Gene(models.Model):

    # previously data.orf field, corresponds to 4. Feature name, YAL*
    systematic_name = models.CharField(
        max_length=50, null=True, blank=True, unique=True
    )

    # corresponds to 1. Primary SGDID, intended to query SGD API if needed
    # NOTE: unique removed from here and common name in the case of blank
    primary_sgdid = models.CharField(max_length=50, null=True, blank=True)

    # Corresponds to 5. Standard gene name, if defined
    common_name = models.CharField(max_length=50, null=True, blank=True)

    # Corresponds to 6. Alias (optional, multiples separated by |)
    aliases = models.ManyToManyField(GeneAlias, blank=True)

    common_name_explanation = models.CharField(max_length=255, null=True, blank=True)
    description = models.TextField(null=True, blank=True)

    objects = GeneManager()

    # TODO: additional mutations resulting from perturbing gene
    # genome_alterations, acquired_secondary_alterations

    def __str__(self):
        return "%s / %s" % (self.common_name, self.systematic_name)

    def aliases_list_as_str(self):
        return "; ".join([str(a) for a in self.aliases.all()])

    def link_detail(self):
        """Return the link for the gene detail"""
        return '<a href="%s">%s</a>' % (reverse("genes:detail", args=[self.id]), self)

    def get_scores(self, ascending=True):
        data = self.data.filter(dataset__data_source__release=True).filter(valuez__isnull=False)
        data = data.values("valuez", "dataset_id",
                           dataset_name=F("dataset__name"))
        data = data.order_by("valuez") if ascending else data.order_by("-valuez")
        data = update_values_with_percentile(data, "valuez")
        return data

    def get_similarities(self, ascending=True):
        data = self.similarities.values("score", "pvalue", "gene2_id", "gene2__systematic_name", "gene2__common_name")
        data = data.order_by("score") if ascending else data.order_by("-score")
        data = update_values_with_percentile(data, "score")
        return data


class GeneSimilarity(models.Model):
    """A gene similarity is a similarity metric calculated to compare genes
    based on datasets.
    """

    gene1 = models.ForeignKey(
        Gene, on_delete=models.CASCADE, related_name="similarities"
    )
    gene2 = models.ForeignKey(
        Gene, on_delete=models.CASCADE, related_name="gene_similarity2"
    )
    score = models.DecimalField(
        max_digits=10, decimal_places=3
    )
    # IMPORTANT: this is actually a standard deviation
    pvalue = models.DecimalField(max_digits=10, decimal_places=6)

    @property
    def pvalue_scientific_notation(self):
        pass

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

        super(GeneSimilarity, self).save(*args, **kwargs)

    class Meta:
        unique_together = (
            "gene1",
            "gene2",
        )
