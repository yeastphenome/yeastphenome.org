from django.contrib import admin
from yeastphenome.apps.tags.models import Tag
from yeastphenome.apps.common.admin_util import ImprovedModelAdmin


class TagAdmin(ImprovedModelAdmin):
    list_per_page = 50
    list_display = ["name", "description"]
    search_fields = ["name", "description"]
    fields = ("name", "description", "order")
    ordering = ["name"]


admin.site.register(Tag, TagAdmin)
