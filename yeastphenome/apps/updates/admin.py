from django.contrib import admin

from yeastphenome.apps.updates.models import Update
from yeastphenome.apps.common.utils_admin import ImprovedModelAdmin


class UpdateAdmin(ImprovedModelAdmin):
    model = Update
    list_display = (
        "date",
        "title",
        "description",
    )
    fields = (
        "date",
        "title",
        "description",
    )
    search_fields = (
        "date",
        "title",
        "description",
    )


admin.site.register(Update, UpdateAdmin)
