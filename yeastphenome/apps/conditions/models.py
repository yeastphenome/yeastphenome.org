from django.db import models
from django.urls import reverse
from django.apps import apps
from django.db.models import Q
from django.utils.safestring import mark_safe

import re

from yeastphenome.apps.common.utils_format import truncated_list_as_str
from yeastphenome.apps.phenotypes.models import Phenotype
from yeastphenome.apps.tags.models import Tag
from libchebipy import ChebiEntity


class ConditionTypeManager(models.Manager):

    # def all_valid(self):
    #     # Valid = associated with at least 1 dataset from a relevant paper
    #     valid_datasets = apps.get_model("datasets", "Dataset").objects.all_valid()
    #     f = Q(conditions__conditionset__dataset__in=valid_datasets) \
    #         | Q(conditions__medium__dataset__in=valid_datasets)
    #     return self.filter(f).distinct()

    def all_valid(self):
        f1 = Q(conditions__conditionset__dataset__paper__latest_data_status__status__is_valid=True)
        f2 = Q(conditions__medium__dataset__paper__latest_data_status__status__is_valid=True)
        return self.filter(f1 | f2)


class ConditionType(models.Model):

    name = models.CharField(max_length=200, verbose_name="Common name for display")
    other_names = models.TextField(blank=True, null=True)

    pubchem_id = models.PositiveIntegerField(blank=True, null=True, unique=True)
    pubchem_name = models.CharField(max_length=200, blank=True, null=True)

    chebi_id = models.PositiveIntegerField(blank=True, null=True, unique=True)
    chebi_name = models.CharField(max_length=200, blank=True, null=True)

    description = models.TextField(blank=True, null=True)
    tags = models.ManyToManyField(Tag, blank=True)

    objects = ConditionTypeManager()

    class Meta:
        ordering = ["name", "chebi_name", "pubchem_name", "other_names"]

    def __str__(self):
        return u"%s" % self.name

    def all_other_names_list_as_str(self):
        if self.other_names:
            other_names = [name.strip() for name in re.split("[,\n]", self.other_names)]
        else:
            other_names = []
        other_names += [self.chebi_name, self.pubchem_name]
        other_names = list(
            set([name for name in other_names if name and not name == ""])
        )
        return "; ".join(other_names)

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

    def doses_list_as_str(self):
        doses = self.conditions.values_list("dose", flat=True).order_by().distinct()
        return "; ".join(doses)

    def conditions_edit_list(self):
        return mark_safe(", ".join([p.link_edit() for p in self.conditions]))

    def observables_list_as_str(self):
        observables1 = self.conditions.all_valid().values_list("conditionset__dataset__phenotype__observable__name", flat=True)
        observables2 = self.conditions.all_valid().values_list("medium__dataset__phenotype__observable__name", flat=True)

        observables = observables1.union(observables2).order_by().distinct()
        observables = [o for o in observables if o is not None]
        return truncated_list_as_str(observables)

    def papers_list_as_str(self):
        papers1 = self.conditions.values_list("conditionset__dataset__paper__systematic_name", flat=True)
        papers2 = self.conditions.values_list("medium__dataset__paper__systematic_name", flat=True)

        papers = papers1.union(papers2).order_by().distinct()
        papers = [p for p in papers if p is not None]

        return truncated_list_as_str(papers)

    def datasets(self):
        return (
            apps.get_model("datasets", "Dataset")
            .objects.all_valid().filter(
                Q(conditionset__conditions__type=self)
                | Q(medium__conditions__type=self)
            )
            .filter(data_source__release=True)
            .distinct()
        )

    def tags_edit_list(self):
        return mark_safe(", ".join([t.link_edit() for t in self.tags.all()]))

    def tags_list_as_str(self):
        tags_list = self.tags.values_list("name", flat=True)
        return "; ".join(tags_list)

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


class ConditionManager(models.Manager):

    def all_valid(self):
        # Valid = associated with at least 1 dataset from a relevant paper
        valid_datasets = apps.get_model("datasets", "Dataset").objects.all_valid()
        f = Q(conditionset__dataset__in=valid_datasets) \
            | Q(medium__dataset__in=valid_datasets)
        return self.filter(f).distinct()


class Condition(models.Model):
    type = models.ForeignKey(ConditionType, related_name="conditions", on_delete=models.DO_NOTHING)
    dose = models.CharField(max_length=200, null=False, blank=False)
    description = models.TextField(blank=True, null=True)
    modified_on = models.DateField(auto_now=True, null=True)
    tags = models.ManyToManyField(Tag, blank=True)

    objects = ConditionManager()

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


class ConditionSetManager(models.Manager):

    def all_valid(self):
        # Valid = associated with at least 1 dataset from a relevant paper
        valid_datasets = apps.get_model("datasets", "Dataset").objects.all_valid()
        return self.filter(dataset__in=valid_datasets).distinct()


class ConditionSet(models.Model):

    systematic_name = models.CharField(max_length=1000, blank=True, null=True)
    common_name = models.CharField(max_length=200, blank=True, null=True)
    display_name = models.CharField(max_length=1000, blank=True, null=True)

    conditions = models.ManyToManyField(Condition, blank=True)
    description = models.TextField(blank=True, null=True)

    tags = models.ManyToManyField(Tag, blank=True)

    objects = ConditionSetManager()

    def __str__(self):
        if self.display_name:
            return self.display_name
        else:
            return ""

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
            .objects.all_valid().filter(
                Q(datasets__conditionset=self) | Q(datasets__control_conditionset=self)
            ).distinct()
        )

    def papers_all(self):
        ps = (
            apps.get_model("papers", "Paper")
            .objects.filter(
                Q(datasets__conditionset=self) | Q(datasets__control_conditionset=self)
            ).distinct()
        )
        return ps

    def papers_edit_link_list(self):
        return mark_safe(", ".join([p.link_edit() for p in self.papers_all()]))

    def datasets_all(self):
        return (
            apps.get_model("datasets", "Dataset")
            .objects.filter(conditionset=self)
        )

    def datasets(self):
        return (
            apps.get_model("datasets", "Dataset")
            .objects.all_valid().filter(conditionset=self)
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


class MediumManager(models.Manager):

    def all_valid(self):
        # Valid = associated with at least 1 dataset from a relevant paper
        valid_datasets = apps.get_model("datasets", "Dataset").objects.all_valid()
        return self.filter(dataset__in=valid_datasets).distinct()


class Medium(models.Model):

    systematic_name = models.CharField(max_length=1000, blank=True, null=True)
    common_name = models.CharField(max_length=200, blank=True, null=True)
    display_name = models.CharField(max_length=1000, blank=True, null=True)

    conditions = models.ManyToManyField(Condition, blank=True)
    description = models.TextField(blank=True, null=True)

    tags = models.ManyToManyField(Tag, blank=True)

    objects = MediumManager()

    def __str__(self):
        if self.display_name:
            return self.display_name
        else:
            return ""

    def conditions_list_str(self):
        conditions_list = [str(c) for c in self.conditions.all()]
        return mark_safe("; ".join(conditions_list))

    def papers(self):
        return (
            apps.get_model("papers", "Paper")
            .objects.all_valid().filter(Q(datasets__medium=self) | Q(datasets__control_medium=self))
            .distinct()
        )

    def papers_all(self):
        ps = (
            apps.get_model("papers", "Paper")
            .objects.filter(Q(datasets__medium=self) | Q(datasets__control_medium=self))
            .distinct()
        )
        return ps

    def papers_list_str(self):
        papers_list = [str(p) for p in self.papers()]
        return mark_safe("; ".join(papers_list))

    def papers_edit_link_list(self):
        return mark_safe(", ".join([p.link_edit() for p in self.papers_all()]))

    def datasets(self, num=None):
        qs = (
            apps.get_model("datasets", "Dataset")
            .objects.all_valid().filter(medium=self)
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
