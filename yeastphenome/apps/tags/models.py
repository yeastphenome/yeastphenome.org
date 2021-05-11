from django.db import models
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.db.models import Q


class Tag(models.Model):
    name = models.CharField(max_length=200, null=False, blank=False)
    description = models.TextField(max_length=1000, null=True, blank=True)
    order = models.IntegerField(null=True, blank=True)

    def __str__(self):
        return self.name

    @classmethod
    def all_valid(cls, type=''):
        if type == 'conditions':
            return cls.objects.filter(
                Q(condition__isnull=False) | Q(conditiontype__isnull=False)
            ).distinct()
        elif type == 'datasets':
            return cls.objects.filter(dataset__isnull=False)
        elif type == 'phenotypes':
            return cls.objects.filter(observable__isnull=False)
        else:
            return cls.objects.all()

    def link_edit(self):
        html = '<a href="%s">%s</a>' % (
            reverse("admin:tags_tag_change", args=(self.id,)),
            self.name,
        )
        return mark_safe(html)