from django.contrib import admin
from yeastphenome.apps.phenotypes.models import (
    MutantType,
    Observable,
    Phenotype,
    Measurement,
)
from yeastphenome.apps.common.admin_util import ImprovedModelAdmin


class ObservableAdmin(ImprovedModelAdmin):
    list_per_page = 50
    list_display = ["name", "description", "tags_str_list", "papers_str_list"]
    search_fields = ["name", "description", "tags__name"]
    fields = (
        "name",
        "description",
        "tags",
        "phenotypes_edit_link_list",
        "datasets_edit_link_list",
    )
    readonly_fields = (
        "phenotypes_edit_link_list",
        "datasets_edit_link_list",
    )
    raw_id_fields = ("tags",)
    ordering = ["name"]


# class TagAdmin(ImprovedModelAdmin):
#     list_per_page = 50
#     list_display = ["name", "description", "observables_str_list"]
#     search_fields = ["name", "description"]
#     fields = ("name", "description", "observables_edit_link_list")
#     readonly_fields = ("observables_edit_link_list",)
#     ordering = ["name"]


class MutantTypeAdmin(admin.ModelAdmin):
    list_filter = ["name"]
    list_display = ["id", "name", "definition"]
    ordering = ["name"]


class PhenotypeAdmin(ImprovedModelAdmin):
    list_per_page = 50
    list_display = ["name", "observable_name", "reporter", "papers_edit_link_list"]
    search_fields = [
        "name",
        "description",
        "reporter",
        "observable__name",
    ]
    fields = (
        "name",
        "description",
        "observable",
        "reporter",
        "measurement",
        "datasets_edit_link_list",
        "phenotype_siblings_edit_link_list",
    )
    raw_id_fields = (
        "measurement",
        "observable",
    )
    readonly_fields = ("datasets_edit_link_list", "phenotype_siblings_edit_link_list")


class MeasurementAdmin(ImprovedModelAdmin):
    list_display = ["id", "name", "description"]
    ordering = ["id"]
    fields = ("name", "description", "phenotypes_edit_link_list")
    readonly_fields = ("phenotypes_edit_link_list",)


admin.site.register(Phenotype, PhenotypeAdmin)
admin.site.register(MutantType, MutantTypeAdmin)
admin.site.register(Observable, ObservableAdmin)
admin.site.register(Measurement, MeasurementAdmin)
