from django.contrib import admin

from yeastphenome.apps.papers.models import Paper, Status, Statusdata, Statustested
from yeastphenome.apps.papers.forms import PaperModelForm
from yeastphenome.apps.datasets.admin import DatasetInline

from yeastphenome.apps.common.utils_admin import ImprovedModelAdmin
from yeastphenome.apps.common.utils_format import truncated_list_as_str

from yeastphenome.apps.papers.utils import (
    get_pubmed_paper_context,
    get_pubmed_paper,
)


class StatusdataInline(admin.TabularInline):
    model = Statusdata
    extra = 0


class StatustestedInline(admin.TabularInline):
    model = Statustested
    extra = 0


class PaperAdmin(ImprovedModelAdmin):
    list_per_page = 50
    list_display = (
        "pmid",
        "user",
        "systematic_name",
        "datasets_summary",
        "latest_data_status_name_date",
        "latest_tested_status_name",
    )
    list_filter = ["latest_data_status__status__name", "pub_date"]
    ordering = (
        "pub_date",
        "systematic_name",
    )
    fields = [
        ("user",),
        ("systematic_name",),
        ("first_author", "last_author", "pub_date", "pmid"),
        ("title","authors","abstract","citation"),
        ("data_abstract",),
        ("notes", "private_notes"),
        "observables_summary",
        "conditiontypes_summary",
        "tags",
    ]
    raw_id_fields = ("tags",)
    readonly_fields = (
        "systematic_name",
        "title",
        "authors",
        "abstract",
        "citation",
        "observables_summary",
        "conditiontypes_summary",
    )
    inlines = (
        StatusdataInline,
        StatustestedInline,
        DatasetInline,
    )
    search_fields = (
        "pmid",
        "first_author",
        "last_author",
        "private_notes",
        "tags__name",
    )

    form = PaperModelForm

    class Media:
        css = {"all": ("hide_admin_original.css",)}

    def save_model(self, request, obj, form, change):
        pass

    def save_related(self, request, form, formsets, change):
        paper = form.instance

        # If creating a new paper, just save the instance first
        if paper.pk is None:
            super(PaperAdmin, self).save_model(request, paper, form, change)

        # When the paper exists, first save the related data, then update the paper itself
        form.save_m2m()
        for formset in formsets:
            self.save_formset(request, form, formset, change=change)
        if not paper.user:
            paper.user = request.user
        if paper.statusdata_set.all():
            paper.latest_data_status = paper.statusdata_set.latest()
        else:
            paper.latest_data_status = None
        if paper.statustested_set.all():
            paper.latest_tested_status = paper.statustested_set.latest()
        else:
            paper.latest_tested_status = None
        
        observables_list = list(
            paper.datasets.values_list("phenotype__observable__name", flat=True)
            .order_by()
            .distinct()
        )
        paper.observables_summary = truncated_list_as_str(observables_list)

        conditiontypes_list = list(
            paper.datasets.values_list("conditionset__conditions__type__name", flat=True)
            .order_by()
            .distinct()
        )
        paper.conditiontypes_summary = truncated_list_as_str(conditiontypes_list)

        if paper.last_author:
            systematic_name = "%s~%s, %s" % (
                paper.first_author,
                paper.last_author,
                paper.pub_date,
            )
        else:
            systematic_name = "%s, %s" % (paper.first_author, paper.pub_date)
        paper.systematic_name = systematic_name

        # Get PubMed Info
        if paper.pmid != 0:
            xml_data = get_pubmed_paper(paper.pmid)
            context = get_pubmed_paper_context(paper.pmid, xml_data)
            paper.authors = '|'.join(context['authors'])
            paper.title = context['title']
            paper.citation = context['citation']
            paper.abstract = context['abstract']

        super(PaperAdmin, self).save_model(request, paper, form, change)

    def change_view(self, request, object_id, form_url="", extra_context=None):
        extra_context = extra_context or {}
        extra_context["total_num_datasets"] = Paper.objects.get(
            pk=object_id
        ).datasets_number
        return super(PaperAdmin, self).change_view(
            request, object_id, form_url, extra_context=extra_context
        )


class StatusAdmin(admin.ModelAdmin):
    list_display = ("name",)
    ordering = ("name",)


admin.site.register(Paper, PaperAdmin)
admin.site.register(Status, StatusAdmin)
