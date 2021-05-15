from django.db import models
from django.urls import reverse
from django.apps import apps
from django.utils.safestring import mark_safe

from yeastphenome.apps.tags.models import Tag


class Observable(models.Model):
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True)
    modified_on = models.DateField(auto_now=True, null=True)
    tags = models.ManyToManyField(Tag, blank=True)

    @classmethod
    def all_valid(cls):
        return cls.objects.filter(phenotype__isnull=False)

    class Meta:
        get_latest_by = "modified_on"

    def __str__(self):
        return u"%s" % self.name

    def link_edit(self):
        html = '<a href="%s">%s</a>' % (
            reverse("admin:phenotypes_observable_change", args=(self.id,)),
            self,
        )
        return mark_safe(html)

    def tags_str_list(self):
        tags_list = self.tags.all().values_list("name", flat=True)
        return mark_safe("; ".join(tags_list))

    def tags_edit_link_list(self):
        html = "<ul>"
        html = html + "<li>".join([p.link_edit() for p in self.tags.all()])
        html = html + "</ul>"
        return mark_safe(html)

    def phenotypes(self):
        return (
            apps.get_model("phenotypes", "Phenotype")
            .objects.filter(observable=self)
            .distinct()
        )

    def phenotypes_list(self):
        return "; ".join([str(p) for p in self.phenotypes()[:20]])

    def phenotypes_edit_link_list(self):
        html = "<ul>"
        html = html + "<li>".join([p.link_edit() for p in self.phenotypes()[:20]])
        html = html + "</ul>"
        return mark_safe(html)

    def reporters(self):
        return self.phenotype_set.exclude(reporter=None).values_list(
            "reporter", flat=True
        )

    def reporters_list_str(self):
        return mark_safe("; ".join(self.reporters()))

    def datasets(self):
        return (
            apps.get_model("datasets", "Dataset")
            .objects.filter(phenotype__observable=self)
            .all()
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

    def conditiontypes(self):
        return (
            apps.get_model("conditions", "ConditionType")
            .objects.filter(
                condition__conditionset__dataset__phenotype__observable=self
            )
            .exclude(
                condition__conditionset__dataset__paper__latest_data_status__status__name="not relevant"
            )
            .distinct()
            .order_by("name")
        )

    def conditiontypes_list_str(self):
        conditiontypes_list = self.conditiontypes().values_list("name", flat=True)
        return mark_safe("; ".join(conditiontypes_list))

    def papers(self):
        return (
            apps.get_model("papers", "Paper")
            .objects.filter(dataset__phenotype__observable=self)
            .exclude(latest_data_status__status__name="not relevant")
            .distinct()
            .order_by("first_author")
        )

    def papers_str_list(self):
        return "; ".join([(u"%s" % p) for p in self.papers()])


class Measurement(models.Model):
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)

    @classmethod
    def all_valid(cls):
        return cls.objects.all()

    def __str__(self):
        return u"%s" % self.name

    def phenotypes(self):
        return apps.get_model("phenotypes", "Phenotype").objects.filter(
            measurement=self
        )

    def phenotypes_edit_link_list(self):
        html = "<ul>"
        html = html + "<li>".join([ph.link_edit() for ph in self.phenotypes()[:20]])
        html = html + "</ul>"
        return mark_safe(html)


class Phenotype(models.Model):
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True)
    observable = models.ForeignKey(
        Observable, blank=False, null=False, on_delete=models.CASCADE
    )
    # an entity that gives us evidence for an observable
    reporter = models.CharField(max_length=200, blank=True, null=True)
    measurement = models.ForeignKey(
        Measurement, blank=True, null=True, on_delete=models.DO_NOTHING
    )
    modified_on = models.DateField(auto_now=True, null=True)

    def __str__(self):
        if self.reporter:
            return u"%s (%s)" % (self.observable, self.reporter)
        else:
            return u"%s" % self.observable

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
            .objects.filter(dataset__phenotype=self)
            .exclude(latest_data_status__status__name="not relevant")
            .distinct()
        )

    @classmethod
    def all_valid(cls):
        return cls.objects.filter(dataset__isnull=False)

    def papers_all(self):
        return (
            apps.get_model("papers", "Paper")
            .objects.filter(dataset__phenotype=self)
            .distinct()
        )

    def papers_edit_link_list(self):
        return mark_safe(", ".join([p.link_edit() for p in self.papers_all()]))

    def datasets(self):
        return (
            apps.get_model("datasets", "Dataset").objects.filter(phenotype=self).all()
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


class MutantType(models.Model):
    name = models.CharField(max_length=200)
    definition = models.TextField(blank=True)

    @classmethod
    def all_valid(cls):
        return cls.objects.all()

    def __str__(self):
        return u"%s" % self.name
