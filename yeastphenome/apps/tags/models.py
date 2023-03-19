from django.db import models
from django.urls import reverse
from django.utils.safestring import mark_safe

from yeastphenome.apps.tags.managers import TagManager


class Tag(models.Model):
    name = models.CharField(max_length=200, null=False, blank=False)
    description = models.TextField(max_length=1000, null=True, blank=True)
    order = models.IntegerField(null=True, blank=True)

    objects = TagManager()

    def __str__(self):
        return self.name

    class Meta:
        ordering = ["name"]

    def link_detail(self):
        html = '<a href="/search/?q=%s">%s</a>' % (self.name, self.name)
        return mark_safe(html)

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
