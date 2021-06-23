from django.db import models
from django.db.models import Q
from django.urls import reverse
from django.apps import apps
from django.utils.safestring import mark_safe

from yeastphenome.apps.datasets.models import Dataset
from yeastphenome.apps.tags.models import Tag
from yeastphenome.settings import (
    ELASTICSEARCH_HOST,
    ELASTICSEARCH_AUTH
)

from elastic_enterprise_search import AppSearch

from urllib.parse import quote_plus


class ObservableManager(models.Manager):

    def all_valid(self):
        valid_datasets = Dataset.objects.all_valid()
        f = Q(phenotype__dataset__in=valid_datasets)
        return self.filter(f).distinct()


class Observable(models.Model):
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True)
    modified_on = models.DateField(auto_now=True, null=True)
    tags = models.ManyToManyField(Tag, blank=True, related_name="observables")

    objects = ObservableManager()

    class Meta:
        get_latest_by = "modified_on"

    def __str__(self):
        return u"%s" % self.name

    def is_valid(self):
        valid_datasets = Dataset.objects.all_valid()
        valid_phenotypes = self.phenotype_set.filter(dataset__in=valid_datasets)
        return valid_phenotypes.exists()

    def link_edit(self):
        html = '<a href="%s">%s</a>' % (
            reverse("admin:phenotypes_observable_change", args=(self.id,)),
            self,
        )
        return mark_safe(html)

    def tags_list(self):
        return list(self.tags.values_list("name", flat=True))

    def tags_list_as_str(self):
        return "; ".join(self.tags_list())

    def tags_list_as_links(self):
        link_template = '<a class="search" href="/search/?q=%s&field=tags&tab=phenotypes">%s</a>'
        tags_list = self.tags_list()
        tags_list_links = [(link_template % (quote_plus(tag), tag)) for tag in tags_list]
        if len(tags_list) > 1:
            tags_all = [link_template % (quote_plus(self.tags_list_as_str()), "all")]
        else:
            tags_all = []
        html1 = ["; ".join(tags_list_links)]
        html2 = tags_all
        html = "   |   ".join(html1 + html2)
        return mark_safe(html)

    def tags_edit_link_list(self):
        html = "<ul>"
        html = html + "<li>".join([p.link_edit() for p in self.tags.all()])
        html = html + "</ul>"
        return mark_safe(html)

    def phenotypes(self):
        return self.phenotype_set.all()

    def phenotypes_list(self):
        return self.phenotypes().values_list("name", flat=True)

    def phenotypes_list_as_str(self):
        return "; ".join(self.phenotypes_list())

    def phenotypes_edit_link_list(self):
        html = "<ul>"
        html = html + "<li>".join([p.link_edit() for p in self.phenotypes()[:20]])
        html = html + "</ul>"
        return mark_safe(html)

    def reporters(self):
        return self.phenotype_set.all_valid().exclude(reporter=None).exclude(reporter="").values_list(
            "reporter", flat=True
        ).order_by().distinct()

    def reporters_list(self):
        return list(self.reporters())

    def reporters_list_as_str(self):
        return "; ".join(self.reporters_list())

    def datasets(self):
        return (
            apps.get_model("datasets", "Dataset")
            .objects.all_valid().filter(phenotype__observable=self)
        )

    def datasets_edit_link_list(self):
        html = "<ul>"
        html = html + "<li>".join([d.link_edit() for d in self.datasets()[:50]])
        html = html + "</ul>"
        return mark_safe(html)

    def link_detail(self):
        html = '<a href="%s">%s</a>' % (
            reverse("phenotypes:detail", args=(self.id,)),
            self,
        )
        return mark_safe(html)

    def conditiontypes_list_as_str(self):
        conditiontypes = self.phenotype_set.all_valid().values_list(
            "dataset__conditionset__conditions__type__name", flat=True).order_by().distinct()
        conditiontypes = [c for c in conditiontypes if c]
        return "; ".join(conditiontypes)

    def papers_list_as_str(self):
        # 2X faster than Paper.objects.all_valid().filter(dataset__phenotype__observable=self)
        papers = self.phenotype_set.all_valid().values_list("dataset__paper__systematic_name",
                                                            flat=True).order_by().distinct()
        papers = [p for p in papers if p]
        return "; ".join(papers)

    def data_indexing(self):
        json = {"id": self.id,
                "name": self.name,
                "description": self.description,
                "phenotypes_list_as_str": self.phenotypes_list_as_str(),
                "reporters_list_as_str": self.reporters_list_as_str(),
                "conditiontypes_list_as_str": self.conditiontypes_list_as_str(),
                "papers_list_as_str": self.papers_list_as_str(),
                "tags_list_as_str": self.tags_list_as_str()}
        return json

    def update_indexing(self, mode="create"):

        app_search = AppSearch(
            ELASTICSEARCH_HOST,
            http_auth=ELASTICSEARCH_AUTH,
        )

        if mode == "update":
            resp = app_search.put_documents(
                engine_name="observables",
                documents=[self.data_indexing()]
            )
        elif mode == "delete":
            resp = app_search.delete_documents(
                engine_name="observables",
                document_ids=[self.id]
            )
        elif mode == "create":
            resp = app_search.index_documents(
                engine_name="observables",
                documents=[self.data_indexing()]
            )

        # Update related indices
        datasets = apps.get_model("datasets", "Dataset").objects.all_valid()
        datasets = datasets.filter(phenotype__observable=self).distinct()
        documents = [dataset.data_indexing() for dataset in datasets]
        resp = app_search.put_documents(
            engine_name="datasets", documents=documents)

        conditiontypes = apps.get_model("conditions", "ConditionType").objects.all()
        conditiontypes = conditiontypes.filter(conditions__conditionset__dataset__in=datasets).distinct()
        documents = [conditiontype.data_indexing() for conditiontype in conditiontypes]
        resp = app_search.put_documents(
            engine_name="conditiontypes", documents=documents)

        papers = apps.get_model("papers", "Paper").objects.all_valid()
        papers = papers.filter(datasets__in=datasets).distinct()
        documents = [paper.data_indexing() for paper in papers]
        resp = app_search.put_documents(
            engine_name="papers", documents=documents)
        # print(resp)


class Measurement(models.Model):
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)

    def __str__(self):
        return u"%s" % self.name

    def phenotypes(self):
        return apps.get_model("phenotypes", "Phenotype").objects.all_valid().filter(
            measurement=self
        )

    def phenotypes_edit_link_list(self):
        html = "<ul>"
        html = html + "<li>".join([ph.link_edit() for ph in self.phenotypes()[:20]])
        html = html + "</ul>"
        return mark_safe(html)


class PhenotypeManager(models.Manager):

    def all_valid(self):
        # Valid = is associated with >=1 valid dataset
        valid_datasets = Dataset.objects.all_valid()
        return self.filter(dataset__in=valid_datasets)


class Phenotype(models.Model):
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True)
    observable = models.ForeignKey(
        Observable, blank=False, null=False, on_delete=models.CASCADE
    )
    reporter = models.CharField(max_length=200, blank=True, null=True)
    measurement = models.ForeignKey(
        Measurement, blank=True, null=True, on_delete=models.DO_NOTHING
    )
    tags = models.ManyToManyField(Tag, blank=True, related_name="phenotypes")
    modified_on = models.DateField(auto_now=True, null=True)

    objects = PhenotypeManager()

    def __str__(self):
        if self.reporter:
            return u"%s (%s)" % (self.observable, self.reporter)
        else:
            return u"%s" % self.observable

    def aliases_list(self):
        lst = list({str(self), self.name, self.observable.name})
        return lst

    def link_detail(self):
        html = '<a href="%s">%s</a>' % (
            reverse("phenotypes:detail", args=(self.observable.id,)),
            self,
        )
        return mark_safe(html)

    def link_edit(self):
        html = '<a href="%s">%s</a>' % (
            reverse("admin:phenotypes_phenotype_change", args=(self.id,)),
            self,
        )
        return mark_safe(html)

    def observable_name(self):
        return self.observable.name

    def papers(self):
        return (
            apps.get_model("papers", "Paper")
            .objects.all_valid().filter(datasets__phenotype=self)
            .distinct()
        )

    def papers_all(self):
        return (
            apps.get_model("papers", "Paper")
            .objects.filter(datasets__phenotype=self)
            .distinct()
        )

    def papers_edit_link_list(self):
        return mark_safe(", ".join([p.link_edit() for p in self.papers_all()]))

    def datasets(self):
        return (
            apps.get_model("datasets", "Dataset").objects.all_valid().filter(phenotype=self).all()
        )

    def datasets_edit_link_list(self):
        html = "<ul>"
        html = html + "<li>".join([d.link_edit() for d in self.datasets()[:50]])
        html = html + "</ul>"
        return mark_safe(html)

    def phenotype_siblings_edit_link_list(self):
        siblings = self.observable.phenotype_set.exclude(pk=self.pk).all()
        html = "<ul>"
        html = html + "<li>".join([p.link_edit() for p in siblings[:50]])
        html = html + "</ul>"
        return mark_safe(html)

    def tags_list(self):
        tags_list_self = list(self.tags.values_list("name", flat=True))
        tags_list_observable = self.observable.tags_list()
        tags_list = list(set(tags_list_self + tags_list_observable))
        return tags_list


class MutantType(models.Model):
    name = models.CharField(max_length=200)
    definition = models.TextField(blank=True)

    def __str__(self):
        return u"%s" % self.name
