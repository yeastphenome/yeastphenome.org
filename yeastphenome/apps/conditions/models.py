from django.db import models
from django.urls import reverse
from django.apps import apps
from django.db.models import Q
from django.utils.safestring import mark_safe

from yeastphenome.apps.phenotypes.models import Phenotype
from yeastphenome.apps.tags.models import Tag

from yeastphenome.apps.conditions.managers import (
    ConditionTypeManager, ConditionManager, ConditionSetManager, MediumManager
)

from libchebipy import ChebiEntity
import re
import itertools
from urllib.parse import quote_plus


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

    def get_absolute_url(self):
        return reverse("conditions:detail", args=(self.id,))

    def is_valid(self):
        valid_datasets = apps.get_model("datasets", "Dataset").objects.all_valid()
        valid_conditions = self.conditions.filter(
            conditionset__dataset__in=valid_datasets
        )
        return valid_conditions.exists()

    def aliases_list(self):
        if self.other_names:
            other_names = [name.strip() for name in re.split("[,\n]", self.other_names)]
        else:
            other_names = []
        other_names += [
            self.chebi_name,
            self.pubchem_name,
            str(self.chebi_id),
            str(self.pubchem_id),
        ]
        other_names = list(set([name for name in other_names if name]))
        other_names = [
            name
            for name in other_names
            if name and not name == self.name and not name == "None"
        ]
        return other_names

    def aliases_list_as_str(self):
        return "; ".join(self.aliases_list())

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
        doses = (
            self.conditions.all_valid()
            .values_list("dose", flat=True)
            .order_by()
            .distinct()
        )
        doses = [dose for dose in doses if dose and not dose == "unknown"]
        return "; ".join(doses)

    def conditions_edit_list(self):
        return mark_safe(", ".join([p.link_edit() for p in self.conditions.all()]))

    def observables_list_as_str(self):
        observables1 = self.conditions.all_valid().values_list(
            "conditionset__dataset__phenotype__observable__name", flat=True
        )
        observables = observables1.order_by().distinct()
        observables = [o for o in observables if o]
        return "; ".join(observables)

    def papers_list_as_str(self):
        papers = (
            self.conditions.all_valid()
            .values_list("conditionset__dataset__paper__systematic_name", flat=True)
            .order_by()
            .distinct()
        )
        papers = [p for p in papers if p]
        papers_list = "; ".join(papers)
        return papers_list

    def datasets(self):
        return (
            apps.get_model("datasets", "Dataset")
            .objects.all_valid()
            .filter(
                Q(conditionset__conditions__type=self)
                | Q(medium__conditions__type=self)
            )
            .distinct()
        )

    def tags_edit_list(self):
        return mark_safe(", ".join([t.link_edit() for t in self.tags.all()]))

    def tags_list(self):
        return list(self.tags.values_list("name", flat=True))

    def tags_list_as_str(self):
        return "; ".join(self.tags_list())

    def link_detail(self):
        html = '<a href="%s">%s</a>' % (
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
    type = models.ForeignKey(
        ConditionType, related_name="conditions", on_delete=models.DO_NOTHING
    )
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

    def aliases_list(self):
        aliases = [str(self)] + self.type.aliases_list()
        aliases = list(set(aliases))
        return aliases

    def aliases_list_as_str(self):
        return "; ".join(self.aliases_list())

    def conditionsets(self):
        return ConditionSet.objects.filter(conditions=self).all()

    def media(self):
        return Medium.objects.filter(conditions=self).all()

    def conditionsets_edit_list(self):
        return mark_safe(", ".join([p.link_edit() for p in self.conditionsets()[:20]]))

    def media_edit_list(self):
        return mark_safe(", ".join([p.link_edit() for p in self.media()[:20]]))

    def link_detail(self):
        html = "%s [%s]" % (self.type.link_detail(), self.dose)
        return mark_safe(html)

    def link_edit(self):
        html = '<a href="%s">%s</a>' % (
            reverse("admin:conditions_condition_change", args=(self.id,)),
            self.dose,
        )
        return mark_safe(html)

    def tags_list(self):
        tags_list_self = list(self.tags.values_list("name", flat=True))
        tags_list_conditiontype = self.type.tags_list()
        tags_list = list(set(tags_list_self + tags_list_conditiontype))
        return tags_list

    def tags_edit_list(self):
        return mark_safe(", ".join([t.link_edit() for t in self.tags.all()]))


class ConditionSet(models.Model):

    systematic_name = models.CharField(max_length=1000, blank=True, null=True)
    common_name = models.CharField(max_length=200, blank=True, null=True)
    display_name = models.CharField(max_length=1000, blank=True, null=True)

    conditions = models.ManyToManyField(Condition, blank=True)
    description = models.TextField(blank=True, null=True)

    tags = models.ManyToManyField(Tag, blank=True)

    objects = ConditionSetManager()

    def __str__(self):
        return self.display_name if self.display_name else self.systematic_name

    def aliases_list(self):
        aliases = [self.systematic_name, self.common_name, self.display_name]
        conditions_aliases = list(
            itertools.chain.from_iterable(
                [condition.aliases_list() for condition in self.conditions.all()]
            )
        )
        aliases = list(set(aliases + conditions_aliases))
        aliases = [alias for alias in aliases if alias]
        return aliases

    def aliases_list_as_str(self):
        return "; ".join(self.aliases_list())

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
            .objects.all_valid()
            .filter(
                Q(datasets__conditionset=self) | Q(datasets__control_conditionset=self)
            )
            .distinct()
        )

    def papers_all(self):
        ps = (
            apps.get_model("papers", "Paper")
            .objects.filter(
                Q(datasets__conditionset=self) | Q(datasets__control_conditionset=self)
            )
            .distinct()
        )
        return ps

    def papers_edit_link_list(self):
        return mark_safe(", ".join([p.link_edit() for p in self.papers_all()]))

    def datasets_all(self):
        return apps.get_model("datasets", "Dataset").objects.filter(conditionset=self)

    def datasets(self):
        return (
            apps.get_model("datasets", "Dataset")
            .objects.all_valid()
            .filter(conditionset=self)
        )

    def datasets_edit_list(self):
        html = "<ul>"
        html = html + "<li>".join([d.link_edit() for d in self.datasets_all()])
        html = html + "</ul>"
        return mark_safe(html)

    def phenotypes(self):
        return Phenotype.objects.filter(dataset__conditionset=self).distinct()

    def link_detail(self):
        conditions_link_details = [
            condition.link_detail() for condition in self.conditions.all()
        ]
        return mark_safe("; ".join(conditions_link_details))

    def link_search(self):
        q = quote_plus(str(self))
        html = (
            '<a class="search" '
            'title="Search for other datasets associated with this condition" '
            'href="/search/?q=%s&field=conditions&tab=datasets">%s</a>' % (q, self)
        )
        return mark_safe(html)

    def link_edit(self):
        html = '{<a href="%s">%s</a>}' % (
            reverse("admin:conditions_conditionset_change", args=(self.id,)),
            self,
        )
        return mark_safe(html)

    def tags_list(self):
        tags_list_self = list(self.tags.values_list("name", flat=True))
        tags_list_conditions = list(
            itertools.chain.from_iterable(
                [condition.tags_list() for condition in self.conditions.all()]
            )
        )
        tags_list = list(set(tags_list_self + tags_list_conditions))
        return tags_list


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

    def aliases_list_as_str(self):
        aliases = [self.systematic_name, self.common_name, self.display_name]
        condition_aliases = list(
            itertools.chain(
                condition.aliases_list_as_str() for condition in self.conditions.all()
            )
        )
        aliases = list(set(aliases + condition_aliases))
        aliases = [alias for alias in aliases if alias]
        return "; ".join(aliases)

    def conditions_list_str(self):
        conditions_list = [str(c) for c in self.conditions.all()]
        return mark_safe("; ".join(conditions_list))

    def papers(self):
        return (
            apps.get_model("papers", "Paper")
            .objects.all_valid()
            .filter(Q(datasets__medium=self) | Q(datasets__control_medium=self))
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

    def papers_edit_link_list_20(self):
        lst = [p.link_edit() for p in self.papers_all()[:20]]
        lst_str = ", ".join(lst)
        if self.papers_all().count() > 20:
            lst_str = lst_str + " + more"
        return mark_safe(lst_str)

    def datasets(self, num=None):
        qs = (
            apps.get_model("datasets", "Dataset")
            .objects.all_valid()
            .filter(medium=self)
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
        q = quote_plus(str(self))
        html = (
            '<a class="search" href="/search/?q=%s&field=medium&tab=datasets">%s</a>'
            % (q, self)
        )
        return mark_safe(html)

    def link_edit(self):
        html = '{<a href="%s">%s</a>}' % (
            reverse("admin:conditions_medium_change", args=(self.id,)),
            self,
        )
        return mark_safe(html)

    def tags_list(self):
        tags_list_self = list(self.tags.values_list("name", flat=True))
        tags_list_conditions = list(
            itertools.chain.from_iterable(
                [condition.tags_list() for condition in self.conditions.all()]
            )
        )
        tags_list = list(set(tags_list_self + tags_list_conditions))
        return tags_list

    def tags_list_str(self):
        return mark_safe("; ".join(self.tags_list()))
