from __future__ import unicode_literals

from yeastphenome.apps.datasets.models import Data
from django.core.exceptions import FieldError
from django.db import models
from django.urls import reverse


class GeneAlias(models.Model):
    """A GeneAlias is another name for a gene"""

    name = models.CharField(max_length=250, null=True, blank=True, unique=True)

    def __str__(self):
        return "%s" % self.name

    class Meta:
        db_table = "datasets_genealias"
        app_label = "datasets"


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

    # TODO: additional mutations resulting from perturbing gene
    # genome_alterations, acquired_secondary_alterations

    def __str__(self):
        return "%s / %s" % (self.common_name, self.systematic_name)

    @classmethod
    def all(cls):
        return cls.objects.all()

    def link_detail(self):
        """Return the link for the gene detail"""
        return '<a href="%s">%s</a>' % (reverse("genes:detail", args=[self.id]), self)

    def get_data(self, reverse=False):
        """Filter to data with values defined, sorted greatest to smallest"""
        queryset = (
            Data.objects.filter(gene=self)
            .filter(dataset__data_source__release=True)
            .exclude(valuez__isnull=True)
            .order_by("-valuez")
        )

        if reverse:
            queryset = queryset.reverse()
        return queryset

    def get_ranked_similar(self, reverse=False):
        """Given a gene, get a sorted listed from the most to least similar.
        Assume each pair of genes is represented twice (A-B and B-A).
        """
        queryset = GeneSimilarity.objects.filter(gene1=self).order_by("-score")
        if reverse:
            queryset = queryset.reverse()
        return queryset

    class Meta:
        db_table = "datasets_gene"
        app_label = "datasets"


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
    score = models.DecimalField(
        max_digits=10, decimal_places=3, help_text="z-score of the metric."
    )
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
        app_label = "datasets"
        db_table = "datasets_genesimilarity"
        unique_together = (
            "gene1",
            "gene2",
        )
