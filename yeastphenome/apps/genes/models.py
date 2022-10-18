from __future__ import unicode_literals

from django.core.exceptions import FieldError
from django.db import models
from django.db.models import F

from yeastphenome.apps.datasets.models import Dataset

from yeastphenome.settings import ELASTICSEARCH_HOST, ELASTICSEARCH_AUTH

from elastic_enterprise_search import AppSearch


class GeneAlias(models.Model):

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

    puddu = models.CharField(max_length=50, null=True, blank=True)

    qc_comments = models.TextField(null=True, blank=True)

    objects = GeneManager()

    def __str__(self):
        return "%s / %s" % (self.common_name, self.systematic_name)

    def aliases_list(self):
        return list(self.aliases.all().values_list("name", flat=True))

    def aliases_list_as_str(self):
        return "; ".join(self.aliases_list())

    def get_scores(self):
        datasets = Dataset.objects.all_valid()
        data = self.data.filter(dataset__in=datasets)
        data = data.filter(valuez__isnull=False)
        data = data.values("valuez", "dataset_id", dataset_name=F("dataset__name"))
        return data

    def get_similarities(self):
        data = self.similarities.values(
            "score",
            "pvalue",
            "gene2_id",
            "gene2__systematic_name",
            "gene2__common_name",
        )
        return data

    def data_indexing(self):
        json = {
            "id": self.id,
            "systematic_name": self.systematic_name,
            "common_name": self.common_name,
            "aliases_list_as_str": self.aliases_list_as_str(),
            "description": self.description,
        }
        return json

    def update_indexing(self, mode="create"):

        app_search = AppSearch(
            ELASTICSEARCH_HOST,
            http_auth=ELASTICSEARCH_AUTH,
        )

        if mode == "update":
            _ = app_search.put_documents(
                engine_name="genes", documents=[self.data_indexing()]
            )
        elif mode == "delete":
            _ = app_search.delete_documents(engine_name="genes", document_ids=[self.id])
        elif mode == "create":
            _ = app_search.index_documents(
                engine_name="genes", documents=[self.data_indexing()]
            )
        # print(resp)


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
    score = models.DecimalField(max_digits=10, decimal_places=3)
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
