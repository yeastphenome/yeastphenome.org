from django.contrib import admin

from yeastphenome.apps.genes.models import Gene, GeneAlias
from yeastphenome.apps.common.admin_util import ImprovedModelAdmin


class GeneAdmin(ImprovedModelAdmin):
    model = Gene
    list_display = (
        "id",
        "systematic_name",
        "common_name",
    )
    fields = (
        "id",
        "systematic_name",
        "common_name",
    )


class GeneAliasAdmin(ImprovedModelAdmin):
    model = GeneAlias
    list_display = (
        "id",
        "name",
    )
    fields = (
        "id",
        "name",
    )
    ordering = ("name",)


admin.site.register(Gene, GeneAdmin)
admin.site.register(GeneAlias, GeneAliasAdmin)
