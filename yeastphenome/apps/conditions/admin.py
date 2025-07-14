from django.contrib import admin
from django.urls import reverse
from django import forms
from django.db.models import Min
from django.utils.safestring import mark_safe

import re

from yeastphenome.apps.conditions.models import (
    ConditionSet,
    Condition,
    ConditionType,
    Medium,
)
from yeastphenome.apps.common.utils_admin import (
    ImprovedTabularInline,
    ImprovedModelAdmin,
)


class ConditionAdminForm(forms.ModelForm):
    def clean(self):
        cleaned_data = super(ConditionAdminForm, self).clean()
        dose = cleaned_data.get("dose")
        if dose is None or dose == "":
            self.add_error("dose", 'If unsure about the value, insert "unknown".')
        return cleaned_data


class ConditionAdmin(ImprovedModelAdmin):
    form = ConditionAdminForm
    list_per_page = 25
    list_display = (
        "id",
        "type",
        "dose",
        # "conditionsets_edit_list",
        # "media_edit_list",
        "tags_edit_list",
    )
    ordering = ("type__name", "dose")
    fields = [
        "type",
        "dose",
        "description",
        "tags",
    ]
    search_fields = (
        "type__name",
        "type__other_names",
        "type__pubchem_name",
        "type__chebi_name",
        "type__pubchem_id",
        "type__chebi_id",
        "dose",
        "tags__name",
    )
    raw_id_fields = (
        "type",
        "tags",
    )


class ConditionInline(ImprovedTabularInline):
    model = Condition
    fields = ("id", "admin_change_link")
    readonly_fields = ("id", "admin_change_link")
    ordering = ("dose",)
    extra = 0

    def get_formset(self, request, obj=None, **kwargs):
        if obj:
            self.parent_obj_id = obj.id
        return super(ConditionInline, self).get_formset(request, obj, **kwargs)

    def admin_change_link(self, obj):
        if obj.id:
            html = '<a href="%s?_popup=1" onclick="return showAddAnotherPopup(this);">%s</a>' % (
                reverse("admin:conditions_condition_change", args=(obj.id,)),
                obj.dose,
            )
        else:
            html = (
                '<a href="%s?_popup=1&type=%s" onclick="return showAddAnotherPopup(this);">Create new</a>'
                % (reverse("admin:conditions_condition_add"), self.parent_obj_id)
            )
        return mark_safe(html)


class ConditionTypeAdminForm(forms.ModelForm):
    class Meta:
        widgets = {
            "chebi_id": forms.TextInput,
            "pubchem_id": forms.TextInput,
        }
        fields = "__all__"  # required for Django 3.x


class ConditionTypeAdmin(ImprovedModelAdmin):
    form = ConditionTypeAdminForm
    list_per_page = 25
    list_display = (
        "name",
        "chebi_name",
        "pubchem_name",
        "conditions_edit_list",
        "tags_edit_list",
    )
    ordering = ("name",)
    search_fields = (
        "name",
        "other_names",
        "description",
        "chebi_id",
        "chebi_name",
        "pubchem_id",
        "pubchem_name",
        "tags__name",
    )
    fields = (
        "name",
        "other_names",
        "tags",
        "description",
        "chebi_id",
        "chebi_name",
        "pubchem_id",
        "pubchem_name",
    )
    readonly_fields = (
        "chebi_name",
        "pubchem_name",
    )
    raw_id_fields = ("tags",)
    inlines = (ConditionInline,)

    def save_model(self, request, obj, form, change):

        from libchebipy import ChebiEntity
        from pubchempy import Compound

        # To update ES indexing immediately: save related fields (e.g., tags)
        if not obj.id:
            super().save_model(request, obj, form, change)
        form.save_m2m()

        # # Moved from global import, causes multiple warnings / errors per worker
        # from pubchempy import Compound

        if form.cleaned_data["chebi_id"]:
            chebi_id = form.cleaned_data["chebi_id"]
            chebi_comb = ChebiEntity("CHEBI:" + str(chebi_id))
            parent_id = chebi_comb.get_parent_id()
            if parent_id:
                s = re.findall(r"\d+", parent_id)
                chebi_id = int(s[0])
                chebi_comb = ChebiEntity("CHEBI:" + str(chebi_id))
            obj.chebi_id = chebi_id
            obj.chebi_name = chebi_comb.get_name()
        else:
            obj.chebi_name = None

        if form.cleaned_data["pubchem_id"]:
            comp = Compound.from_cid(form.cleaned_data["pubchem_id"])

            # Not all compounds have synonyms, fall back to iupac_name
            if comp.synonyms:
                obj.pubchem_name = comp.synonyms[0]
            else:
                obj.pubchem_name = comp.iupac_name
        else:
            obj.pubchem_name = None

        super().save_model(request, obj, form, change)


class ConditionSetAdmin(ImprovedModelAdmin):
    list_per_page = 25
    list_display = (
        "id",
        "display_name",
        "papers_edit_link_list",
    )
    raw_id_fields = ("conditions", "tags")
    search_fields = (
        "systematic_name",
        "common_name",
        "conditions__type__name",
        "conditions__type__other_names",
        "conditions__type__pubchem_name",
        "conditions__type__chebi_name",
        "tags__name",
    )
    ordering = (
        "id",
        "display_name",
    )

    fields = (
        "systematic_name",
        "common_name",
        "display_name",
        "conditions",
        "description",
        "tags",
        "datasets_edit_list",
    )
    readonly_fields = (
        "systematic_name",
        "display_name",
        "datasets_edit_list",
    )

    def save_model(self, request, obj, form, change):

        obj.save()
        form.save_m2m()

        conditions_list = [
            (u"%s" % condition)
            for condition in obj.conditions.annotate(
                tags_order=Min("type__tags__order")
            )
            .order_by(
                "tags_order", "type__name", "type__chebi_name", "type__pubchem_name"
            )
            .all()
        ]
        conditions_str = ", ".join(conditions_list)
        obj.systematic_name = (
            conditions_str[:1000] if len(conditions_str) > 1000 else conditions_str
        )

        obj.display_name = obj.systematic_name
        if obj.common_name:
            obj.display_name = obj.common_name

        obj.save()


class MediumAdmin(ImprovedModelAdmin):
    list_per_page = 25
    list_display = (
        "id",
        "display_name",
        # "papers_edit_link_list_20",
        # "tags_list_str",
    )
    raw_id_fields = ("conditions", "tags")
    search_fields = (
        "systematic_name",
        "common_name",
        "conditions__type__name",
        "conditions__type__other_names",
        "conditions__type__pubchem_name",
        "conditions__type__chebi_name",
        "tags__name",
    )
    ordering = (
        "id",
        "display_name",
    )

    fields = (
        "systematic_name",
        "common_name",
        "display_name",
        "conditions",
        "description",
        "tags",
        "datasets_edit_link_list_top50",
    )
    readonly_fields = (
        "systematic_name",
        "display_name",
        "datasets_edit_link_list_top50",
    )

    def save_model(self, request, obj, form, change):

        obj.save()
        form.save_m2m()

        conditions_list = [
            (u"%s" % condition)
            for condition in obj.conditions.annotate(
                tags_order=Min("type__tags__order")
            )
            .order_by(
                "tags_order", "type__name", "type__chebi_name", "type__pubchem_name"
            )
            .all()
        ]
        conditions_str = ", ".join(conditions_list)
        obj.systematic_name = (
            conditions_str[:1000] if len(conditions_str) > 1000 else conditions_str
        )

        obj.display_name = obj.systematic_name
        if obj.common_name:
            obj.display_name = obj.common_name

        obj.save()


admin.site.register(Condition, ConditionAdmin)
admin.site.register(ConditionType, ConditionTypeAdmin)
admin.site.register(ConditionSet, ConditionSetAdmin)
admin.site.register(Medium, MediumAdmin)
