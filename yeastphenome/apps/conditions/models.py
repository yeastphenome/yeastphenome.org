from django.db import models
from django.urls import reverse
from django.apps import apps
from django.db.models import Q, Count
from django.utils.safestring import mark_safe

import re

from yeastphenome.apps.phenotypes.models import Phenotype
from yeastphenome.apps.tags.models import Tag
from libchebipy import ChebiEntity


class ConditionType(models.Model):
    """A ConditionType can be temperature, treatment, etc."""

    name = models.CharField(max_length=200, verbose_name="common name for display")
    other_names = models.TextField(blank=True, null=True)

    pubchem_id = models.PositiveIntegerField(blank=True, null=True, unique=True)
    pubchem_name = models.CharField(max_length=200, blank=True, null=True)

    chebi_id = models.PositiveIntegerField(blank=True, null=True, unique=True)
    chebi_name = models.CharField(max_length=200, blank=True, null=True)

    description = models.TextField(blank=True, null=True)
    tags = models.ManyToManyField(Tag, blank=True)

    class Meta:
        ordering = ["name", "chebi_name", "pubchem_name", "other_names"]

    @classmethod
    def all_valid(cls):
        return cls.objects.annotate(
            number_of_datasets=Count(
                "condition__conditionset__dataset",
                filter=~Q(
                    condition__conditionset__dataset__paper__latest_data_status__status__name="not relevant"
                ),
            )
        ).filter(number_of_datasets__gte=1)

    def __str__(self):
        if self.name:
            type_name = self.name
        elif self.chebi_name:
            type_name = self.chebi_name
        elif self.pubchem_name:
            type_name = self.pubchem_name
        else:
            type_name = self.other_names
        return u"%s" % type_name

    def all_other_names(self):
        if self.other_names:
            other_names = [name.strip() for name in re.split("[,\n]", self.other_names)]
        else:
            other_names = []
        other_names += [self.chebi_name, self.pubchem_name]
        other_names = list(
            set([name for name in other_names if name and not name == ""])
        )
        return mark_safe("; ".join(other_names))

    def definition(self):
        if self.chebi_id:
            entity = ChebiEntity("CHEBI:" + str(self.chebi_id))
            return entity.get_definition()
        else:
            return ""

    def has_roles(self):
        if self.chebi_id:
            entity = ChebiEntity("CHEBI:" + str(self.chebi_id))
            outdict = dict()
            for relation in entity.get_outgoings():
                if relation.get_type() == "has_role":
                    tid = relation.get_target_chebi_id()
                    t = ChebiEntity(tid)
                    s = re.findall(r"\d+", tid)
                    outdict[t.get_name()] = int(s[0])
            return outdict
        else:
            return ""

    def conditions(self):
        return Condition.objects.filter(type=self).order_by("dose")

    def doses_str_list(self):
        doses = self.conditions().values_list("dose", flat=True)
        return mark_safe("; ".join(doses))

    def conditions_edit_list(self):
        return mark_safe(", ".join([p.link_edit() for p in self.conditions()]))

    def phenotypes(self):
        return (
            Phenotype.objects.filter(
                Q(dataset__conditionset__conditions__type=self)
                | Q(dataset__medium__conditions__type=self)
            )
            .distinct()
            .order_by("observable__name")
        )

    def observables_list_str(self):
        observables = self.phenotypes().values_list("observable__name", flat=True)
        return mark_safe("; ".join(observables))

    def papers(self):
        return (
            apps.get_model("papers", "Paper")
            .objects.filter(
                Q(datasets__conditionset__conditions__type=self)
                | Q(datasets__medium__conditions__type=self)
            )
            .exclude(latest_data_status__status__name="not relevant")
            .distinct()
            .order_by("first_author")
        )

    def datasets(self):
        return (
            apps.get_model("datasets", "Dataset")
            .objects.filter(
                Q(conditionset__conditions__type=self)
                | Q(medium__conditions__type=self)
            )
            .exclude(paper__latest_data_status__status__name="not relevant")
            .filter(data_source__release=True)
            .distinct()
        )

    def tags_edit_list(self):
        return mark_safe(", ".join([t.link_edit() for t in self.tags.all()]))

    def tags_list_str(self):
        tags_list = self.tags.all().values_list("name", flat=True)
        return mark_safe("; ".join(tags_list))

    def link_detail(self):
        html = '<a id="condition-%s" href="%s">%s</a>' % (
            self.id,
            reverse("conditions:detail", args=(self.id,)),
            self,
        )
        return mark_safe(html)

    def link_edit(self):
        html = '<a href="%s">%s</a>' % (
            reverse("admin:conditions_conditiontype_change", args=(self.id,)),
            self,
        )
        return mark_safe(html)


class Condition(models.Model):
    type = models.ForeignKey(ConditionType, on_delete=models.DO_NOTHING)
    dose = models.CharField(max_length=200, null=False, blank=False)
    description = models.TextField(blank=True, null=True)
    modified_on = models.DateField(auto_now=True, null=True)
    tags = models.ManyToManyField(Tag, blank=True)

    @classmethod
    def all_valid(cls):
        return cls.objects.annotate(
            number_of_datasets=Count(
                "conditionset__dataset",
                filter=~Q(
                    conditionset__dataset__paper__latest_data_status__status__name="not relevant"
                ),
            )
        ).filter(number_of_datasets__gte=1)

    class Meta:
        get_latest_by = "modified_on"

    def __str__(self):
        if self.dose in ["standard", "unknown"]:
            txt = u"%s" % self.type
        else:
            txt = u"%s [%s]" % (self.type, self.dose)
        return txt

    def conditionsets(self):
        return ConditionSet.objects.filter(conditions=self).all()

    def media(self):
        return Medium.objects.filter(conditions=self).all()

    def conditionsets_edit_list(self):
        return mark_safe(", ".join([p.link_edit() for p in self.conditionsets()[:20]]))

    def media_edit_list(self):
        return mark_safe(", ".join([p.link_edit() for p in self.media()[:20]]))

    def link_detail(self):
        html = '<a href="%s">%s</a>' % (
            reverse("conditions:detail", args=(self.type.id,)),
            self,
        )
        return mark_safe(html)

    def link_edit(self):
        html = '<a href="%s">%s</a>' % (
            reverse("admin:conditions_condition_change", args=(self.id,)),
            self.dose,
        )
        return mark_safe(html)

    def tags_edit_list(self):
        return mark_safe(", ".join([t.link_edit() for t in self.tags.all()]))


class ConditionSet(models.Model):

    systematic_name = models.CharField(max_length=1000, blank=True, null=True)
    common_name = models.CharField(max_length=200, blank=True, null=True)
    display_name = models.CharField(max_length=1000, blank=True, null=True)

    conditions = models.ManyToManyField(Condition, blank=True)
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        if self.display_name:
            return self.display_name
        else:
            return ""

    @classmethod
    def all_valid(cls):
        return cls.objects.filter(dataset__isnull=False)

    # # Necessary to run database-wide updates of conditionset names
    # def save(self, *args, **kwargs):
    #
    #     # Generate the systematic name
    #     conditions_list = [(u'%s' % condition) for condition in
    #                        self.conditions.order_by('type__group__order', 'type__chebi_name', 'type__pubchem_name',
    #                                                 'type__name').all()]
    #     self.systematic_name = u'%s' % ", ".join(conditions_list)
    #     self.display_name = self.systematic_name
    #     if self.common_name:
    #         self.display_name = self.common_name
    #     super(ConditionSet, self).save(*args, **kwargs)

    def papers(self):
        return (
            apps.get_model("papers", "Paper")
            .objects.filter(
                Q(dataset__conditionset=self) | Q(dataset__control_conditionset=self)
            )
            .exclude(latest_data_status__status__name="not relevant")
            .distinct()
        )

    def papers_all(self):
        ps = (
            apps.get_model("papers", "Paper")
            .objects.filter(
                Q(dataset__conditionset=self) | Q(dataset__control_conditionset=self)
            )
            .distinct()
        )
        return ps

    def papers_edit_link_list(self):
        return mark_safe(", ".join([p.link_edit() for p in self.papers_all()]))

    def datasets_all(self):
        return (
            apps.get_model("datasets", "Dataset")
            .objects.filter(conditionset=self)
            .distinct()
        )

    def datasets(self):
        return self.datasets_all().exclude(
            paper__latest_data_status__status__name="not relevant"
        )

    def datasets_edit_list(self):
        html = "<ul>"
        html = html + "<li>".join([d.link_edit() for d in self.datasets_all()])
        html = html + "</ul>"
        return mark_safe(html)

    def phenotypes(self):
        return Phenotype.objects.filter(dataset__conditionset=self).distinct()

    def link_detail(self):
        html = '<a href="%s">%s</a>' % (
            reverse("conditions:conditionset_detail", args=(self.id,)),
            self,
        )
        return mark_safe(html)

    def link_edit(self):
        html = '{<a href="%s">%s</a>}' % (
            reverse("admin:conditions_conditionset_change", args=(self.id,)),
            self,
        )
        return mark_safe(html)


class Medium(models.Model):

    systematic_name = models.CharField(max_length=1000, blank=True, null=True)
    common_name = models.CharField(max_length=200, blank=True, null=True)
    display_name = models.CharField(max_length=1000, blank=True, null=True)

    conditions = models.ManyToManyField(Condition, blank=True)
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        if self.display_name:
            return self.display_name
        else:
            return ""

    @classmethod
    def all_valid(cls):
        return cls.objects.all()

    def conditions_str_list(self):
        return ", ".join([str(c) for c in self.conditions.all()])

    def papers(self):
        return (
            apps.get_model("papers", "Paper")
            .objects.filter(Q(dataset__medium=self) | Q(dataset__control_medium=self))
            .exclude(latest_data_status__status__name="not relevant")
            .distinct()
        )

    def papers_all(self):
        ps = (
            apps.get_model("papers", "Paper")
            .objects.filter(Q(dataset__medium=self) | Q(dataset__control_medium=self))
            .distinct()
        )
        return ps

    def paper_str_list(self):
        return ", ".join([str(p) for p in self.papers()])

    def papers_edit_link_list(self):
        return mark_safe(", ".join([p.link_edit() for p in self.papers_all()]))

    def datasets(self, num=None):
        qs = (
            apps.get_model("datasets", "Dataset")
            .objects.filter(medium=self)
            .exclude(paper__latest_data_status__status__name="not relevant")
            .distinct()
        )
        if num:
            qs = qs[:num]
        return qs

    def datasets_all(self, num=None):
        qs = (
            apps.get_model("datasets", "Dataset").objects.filter(medium=self).distinct()
        )
        if num:
            qs = qs[:num]
        return qs

    def datasets_edit_link_list(self, num=None):
        qs = self.datasets_all(num=num)
        html = "<ul>"
        html = html + "<li>".join([d.link_edit() for d in qs])
        html = html + "</ul>"
        return mark_safe(html)

    def datasets_edit_link_list_top50(self):
        return mark_safe(self.datasets_edit_link_list(num=50))

    def phenotypes(self):
        return Phenotype.objects.filter(dataset__medium=self).distinct()

    def link_detail(self):
        html = '<a href="%s">%s</a>' % (
            reverse("conditions:medium_detail", args=(self.id,)),
            self,
        )
        return mark_safe(html)

    def link_edit(self):
        html = '{<a href="%s">%s</a>}' % (
            reverse("admin:conditions_medium_change", args=(self.id,)),
            self,
        )
        return mark_safe(html)
