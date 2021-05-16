from django.db import models
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.db.models import Q
from django.apps import apps


class TagManager(models.Manager):

    def all_valid(self, **kwargs):
        obj = self.all()
        if "type" in kwargs:
            if kwargs["type"] == "conditions":
                valid_conditiontypes = apps.get_model("conditions", "Conditiontype").objects.all_valid()
                valid_conditions = apps.get_model("conditions", "Condition").objects.all_valid()
                obj = obj.filter(Q(condition__in=valid_conditions)
                                 | Q(conditiontype__in=valid_conditiontypes)).distinct()
            elif kwargs["type"] == "datasets":
                valid_datasets = apps.get_model("datasets", "Dataset").objects.all_valid()
                obj = obj.filter(dataset__in=valid_datasets)
            elif kwargs["type"] == "phenotypes":
                valid_observables = apps.get_model("phenotype", "Observable").objects.all_valid()
                obj = obj.filter(observable__in=valid_observables)
        return obj


class Tag(models.Model):
    name = models.CharField(max_length=200, null=False, blank=False)
    description = models.TextField(max_length=1000, null=True, blank=True)
    order = models.IntegerField(null=True, blank=True)

    objects = TagManager()

    def __str__(self):
        return self.name

    class Meta:
        ordering = ["name"]

    def link_edit(self):
        html = '<a href="%s">%s</a>' % (
            reverse("admin:tags_tag_change", args=(self.id,)),
            self.name,
        )
        return mark_safe(html)

    def top50_conditiontypes_edit_link_list(self):
        conditiontypes = self.conditiontype_set.order_by("name").all()
        html = "<ul>"
        html += "<li>".join([c.link_edit() for c in conditiontypes[:50]])
        html += "</ul>"
        return mark_safe(html)

    def top50_conditions_edit_link_list(self):
        conditions = self.condition_set.order_by("type__name").all()
        html = "<ul>"
        html += "<li>".join([c.link_edit() for c in conditions[:50]])
        html += "</ul>"
        return mark_safe(html)

    def top50_datasets_edit_link_list(self):
        datasets = self.dataset_set.order_by("name").all()
        html = "<ul>"
        html += "<li>".join([d.link_edit() for d in datasets[:50]])
        html += "</ul>"
        return mark_safe(html)

    def top50_observables_edit_link_list(self):
        observables = self.observable_set.order_by("name").all()
        html = "<ul>"
        html += "<li>".join([p.link_edit() for p in observables[:50]])
        html += "</ul>"
        return mark_safe(html)
