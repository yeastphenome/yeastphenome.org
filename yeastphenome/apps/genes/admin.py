from django.contrib import admin

from yeastphenome.apps.genes.models import Gene, GeneAlias
from yeastphenome.apps.common.admin_util import ImprovedModelAdmin


class GeneAdmin(ImprovedModelAdmin):
    model = Gene
    list_display = (
        "systematic_name",
        "common_name",
        "primary_sgdid",
        "common_name_explanation",
        "description",
    )
    fields = (
        "systematic_name",
        "common_name",
        "primary_sgdid",
        "common_name_explanation",
        "description",
    )

    def save_model(self, request, obj, form, change):

        # To update ES indexing immediately: save related fields (e.g., tags)
        if not obj.id:
            super().save_model(request, obj, form, change)
        form.save_m2m()

        super(GeneAdmin, self).save_model(request, obj, form, change)


class GeneAliasAdmin(ImprovedModelAdmin):
    model = GeneAlias
    list_display = (
        "id",
        "name",
    )
    fields = ("name",)
    ordering = ("name",)


admin.site.register(Gene, GeneAdmin)
admin.site.register(GeneAlias, GeneAliasAdmin)
