from django.contrib import admin
from django.urls import reverse
from django.db import models
from django import forms
from django.utils.http import urlencode
from django.utils.safestring import mark_safe

from yeastphenome.apps.datasets.models import Dataset, Collection, Source
from yeastphenome.apps.common.admin_util import (
    ImprovedModelAdmin,
    ImprovedTabularInline,
    LimitedInlineFormSet,
)


class DatasetAdminForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super(DatasetAdminForm, self).__init__(*args, **kwargs)
        self.fields["name"].widget.attrs["style"] = "width: 35em;"
        self.fields["name"].widget.attrs["readonly"] = True

        self.id = None
        if "instance" in kwargs and kwargs["instance"]:
            self.id = kwargs["instance"].id

    def clean(self):
        cleaned_data = super(DatasetAdminForm, self).clean()
        cleaned_data["name"] = "%s | %s | %s | %s | %s" % (
            cleaned_data["collection"],
            cleaned_data["phenotype"],
            cleaned_data["conditionset"],
            cleaned_data["medium"],
            cleaned_data["paper"],
        )
        qs = Dataset.objects.filter(name=cleaned_data["name"])
        if self.id:
            qs = qs.exclude(pk=self.id)
        if qs.count() > 0:
            self.add_error(
                "name",
                forms.ValidationError("A dataset with this name already exists."),
            )
        return cleaned_data

    class Meta:
        fields = "__all__"
        widgets = {
            "tested_num": forms.TextInput,
        }


class DatasetAdmin(ImprovedModelAdmin):
    model = Dataset
    form = DatasetAdminForm
    fields = (
        "name",
        "paper",
        "conditionset",
        "medium",
        "control_conditionset",
        "control_medium",
        "phenotype",
        "collection",
        "tested_num",
        "tested_list_published",
        "tested_source",
        "data_measured",
        "data_published",
        "data_available",
        "data_source",
        "tags",
        "notes",
    )
    raw_id_fields = (
        "paper",
        "conditionset",
        "medium",
        "control_conditionset",
        "control_medium",
        "phenotype",
        "tested_source",
        "data_source",
        "tags",
    )
    search_fields = (
        "name",
        "tags__name",
    )
    ordering = ("name",)

    save_as = True

    def get_changeform_initial_data(self, request):
        initial = super(DatasetAdmin, self).get_changeform_initial_data(request)
        if "tested_list_published" in initial:
            initial["tested_list_published"] = (
                initial["tested_list_published"] == "True"
            )
        return initial


class DatasetInline(ImprovedTabularInline):
    model = Dataset
    formset = LimitedInlineFormSet
    template = "admin/datasets_inline.html"
    fields = (
        "id",
        "admin_change_link",
        "has_data_in_db",
        "make_a_copy_link",
    )
    readonly_fields = (
        "id",
        "admin_change_link",
        "has_data_in_db",
        "make_a_copy_link",
    )
    ordering = (
        "name",
        "id",
    )
    extra = 0
    max_num = 5000

    def get_formset(self, request, obj=None, **kwargs):
        if obj:
            self.parent_obj_id = obj.id
        return super(DatasetInline, self).get_formset(request, obj, **kwargs)

    def admin_change_link(self, obj):
        if obj.id:
            html = '<a href="%s?_popup=1" onclick="return showAddAnotherPopup(this);">%s</a>' % (
                reverse("admin:datasets_dataset_change", args=(obj.id,)),
                obj.admin_name(),
            )
        else:
            html = (
                '<a href="%s?_popup=1&paper=%s" onclick="return showAddAnotherPopup(this);">Create new</a>'
                % (reverse("admin:datasets_dataset_add"), self.parent_obj_id)
            )
        return mark_safe(html)

    def make_a_copy_link(self, obj):
        query_dict = {"_popup": 1}
        flds = obj._meta.get_fields()
        for f in flds:
            if not (f.many_to_one and f.related_model is None):
                f_name = f.name
                if isinstance(f, models.ForeignKey):
                    f_name += "_id"
                f_value = str(getattr(obj, f_name, "None"))

                # Hacky solution to prevent crash (to solve more permanently)
                if (
                    f.name
                    not in ["id", "tags", "dataset_similarity1", "dataset_similarity2"]
                    and f_value != "None"
                ):
                    query_dict[f.name] = f_value
        query_string = urlencode(query_dict)
        html = (
            '<a id="id_user" href="%s?%s" onclick="return showAddAnotherPopup(this);">Make a copy</a>'
            % (reverse("admin:datasets_dataset_add"), query_string)
        )
        return mark_safe(html)


class DatasetInlineTested(DatasetInline):
    fk_name = "tested_source"
    verbose_name = "Dataset"
    verbose_name_plural = "Datasets with tested strains provided by this source"


class DatasetInlineData(DatasetInline):
    fk_name = "data_source"
    verbose_name = "Dataset"
    verbose_name_plural = "Datasets with data provided by this source"


class SourceAdmin(ImprovedModelAdmin):
    model = Source
    list_display = ("id", "sourcetype", "label", "url")
    fields = ("sourcetype", "label", "url", "date", "release", "acknowledge")
    inlines = [DatasetInlineTested, DatasetInlineData]


class CollectionForm(forms.ModelForm):
    class Meta:
        model = Collection
        fields = "__all__"
        widgets = {
            "ploidy": forms.TextInput,
        }


class CollectionAdmin(ImprovedModelAdmin):
    form = CollectionForm
    list_display = ("__str__", 'is_valid')


class StatusAdmin(ImprovedModelAdmin):
    list_display = ("name",)
    ordering = ("name",)


admin.site.register(Source, SourceAdmin)
admin.site.register(Collection, CollectionAdmin)
admin.site.register(Dataset, DatasetAdmin)
