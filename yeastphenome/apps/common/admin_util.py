from django.contrib import admin
from django.contrib.admin.widgets import ForeignKeyRawIdWidget, ManyToManyRawIdWidget
from django.urls import reverse
from django.utils.html import escape, mark_safe
from django.utils.encoding import smart_str
from django.http import HttpResponse
from django.forms.models import BaseInlineFormSet


class VerboseForeignKeyRawIdWidget(ForeignKeyRawIdWidget):
    """
    A Widget that adds a "popup" to the url of the ForeignKey raw_id label
    """

    def __init__(self, remote_field, attrs=None, *args, **kwargs):
        super().__init__(remote_field, attrs, *args, **kwargs)

    def label_and_url_for_value(self, value):
        return label_and_url_for_value_general(self, [value])


class VerboseManyToManyRawIdWidget(ManyToManyRawIdWidget):
    """
    A Widget that mimics the behavior of ForeignKey raw_id labels but for ManyToMany fields.
    That is: labels + url + popup for all related objects
    """

    def __init__(self, remote_field, attrs=None, *args, **kwargs):
        super().__init__(remote_field, attrs, *args, **kwargs)

    def label_and_url_for_value(self, value):
        return label_and_url_for_value_general(self, value)


def label_and_url_for_value_general(self, values):
    str_values = []
    key = self.rel.get_related_field().name
    fk_model = self.rel.model
    app_label = fk_model._meta.app_label
    class_name = fk_model._meta.object_name.lower()
    for the_value in values:
        try:
            obj = fk_model._default_manager.using(self.db).get(**{key: the_value})
            url = reverse(
                "admin:{0}_{1}_change".format(app_label, class_name), args=[obj.id]
            )
            url += "?_popup=1"
            label = escape(smart_str(obj))
            elt = '<a href="{0}" {1}>{2}</a>'.format(
                url, 'onclick="return showAddAnotherPopup(this);"', label
            )
            str_values += [elt]
        except fk_model.DoesNotExist:
            str_values += [u"???"]
    return mark_safe(", ".join(str_values)), ""


class ImprovedTabularInline(admin.TabularInline):
    def formfield_for_dbfield(self, db_field, **kwargs):
        if db_field.name in self.raw_id_fields:
            field_type = db_field.remote_field.__class__.__name__
            if field_type == "ManyToOneRel":
                kwargs["widget"] = VerboseForeignKeyRawIdWidget(
                    db_field.remote_field, self.admin_site
                )
            elif field_type == "ManyToManyRel":
                kwargs["widget"] = VerboseManyToManyRawIdWidget(
                    db_field.remote_field, self.admin_site
                )
        else:
            return super().formfield_for_dbfield(db_field, **kwargs)
        kwargs.pop("request")
        return db_field.formfield(**kwargs)


class ImprovedModelAdmin(admin.ModelAdmin):
    def formfield_for_dbfield(self, db_field, **kwargs):
        if db_field.name in self.raw_id_fields:
            field_type = db_field.remote_field.__class__.__name__
            if field_type == "ManyToOneRel":
                kwargs["widget"] = VerboseForeignKeyRawIdWidget(
                    db_field.remote_field, self.admin_site
                )
            elif field_type == "ManyToManyRel":
                kwargs["widget"] = VerboseManyToManyRawIdWidget(
                    db_field.remote_field, self.admin_site
                )
        else:
            return super().formfield_for_dbfield(db_field, **kwargs)
        kwargs.pop("request")
        return db_field.formfield(**kwargs)

    def response_change(self, request, obj):
        if request.GET.get("_popup") == "1":
            return HttpResponse(
                '<script type="text/javascript">window.opener.location.reload(); window.close();</script>'
            )
        return super().response_change(request, obj)


class LimitedInlineFormSet(BaseInlineFormSet):
    def get_queryset(self):
        qs = super(BaseInlineFormSet, self).get_queryset()
        return qs[:100]
