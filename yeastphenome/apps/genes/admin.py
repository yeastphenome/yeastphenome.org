from django.contrib import admin
from django.urls import reverse
from django.db import models
from django import forms
from django.utils.http import urlencode
from django.utils.safestring import mark_safe

from yeastphenome.apps.genes.models import Gene, GeneAlias
from yeastphenome.apps.common.admin_util import ImprovedModelAdmin


class GeneAdmin(ImprovedModelAdmin):
    model = Gene
    list_display = ("id", "systematic_name", "common_name",)
    fields = "__all__"
#    fields = ("id", "systematic_name", "common_name")


class GeneAliasAdmin(ImprovedModelAdmin):
    model = GeneAlias
    list_display = ("id", "name",)
    fields = "__all__"
    ordering = ("name",)

#    fields = ("id", "systematic_name", "common_name")

admin.site.register(Gene, GeneAdmin)
admin.site.register(GeneAlias, GeneAliasAdmin)
