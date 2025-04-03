from django.contrib.auth.models import User
from django.db import models
from django.db.models import Q
from django.urls import reverse
from django.utils.safestring import mark_safe

from yeastphenome.apps.tags.models import Tag
from yeastphenome.apps.papers.managers import PaperManager
from yeastphenome.apps.common.utils_format import join_and

import itertools


class Status(models.Model):
    name = models.CharField(max_length=200, default="undefined", blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    is_valid = models.BooleanField()

    def __str__(self):
        return u"%s" % self.name

    class Meta:
        ordering = ["name"]


class Paper(models.Model):

    # PubMed Info
    pmid = models.IntegerField(default=0, unique=True)
    first_author = models.CharField(max_length=200)
    last_author = models.CharField(max_length=200, blank=True, null=True)
    pub_date = models.IntegerField(default=0)
    authors = models.TextField(blank=True, null=True)
    title = models.TextField(blank=True, null=True)
    abstract = models.TextField(blank=True, null=True)
    citation = models.CharField(max_length=200, blank=True, null=True)

    systematic_name = models.CharField(max_length=200, blank=False, null=False)

    notes = models.TextField(blank=True, null=True)
    private_notes = models.TextField(blank=True)
    data_abstract = models.TextField(blank=True, null=True)
    observables_summary = models.TextField(blank=True, null=True)
    conditiontypes_summary = models.TextField(blank=True, null=True)

    tags = models.ManyToManyField(Tag, blank=True)

    user = models.ForeignKey(User, blank=True, null=True, on_delete=models.DO_NOTHING)
    modified_on = models.DateField(auto_now=True)

    data_statuses = models.ManyToManyField(
        Status, through="Statusdata", related_name="data_statuses"
    )
    tested_statuses = models.ManyToManyField(
        Status, through="Statustested", related_name="tested_statuses"
    )

    latest_data_status = models.ForeignKey(
        "Statusdata",
        blank=True,
        null=True,
        related_name="latest_data_status_of_paper",
        on_delete=models.SET_NULL,
    )
    latest_tested_status = models.ForeignKey(
        "Statustested",
        blank=True,
        null=True,
        related_name="latest_tested_status_of_paper",
        on_delete=models.SET_NULL,
    )

    objects = PaperManager()

    class Meta:
        get_latest_by = "modified_on"
        ordering = ["pmid", "systematic_name"]

    def __str__(self):
        return self.systematic_name if self.systematic_name else ""

    def get_absolute_url(self):
        return reverse("papers:detail", args=(self.id,))

    def is_valid(self):
        cond1 = (
            False
            if not self.latest_data_status
            else self.latest_data_status.status.is_valid
        )
        cond2 = self.datasets.all_valid().exists()
        return cond1 & cond2

    def collections_list_as_str(self):
        collections = (
            self.datasets.values_list("collection__shortname", flat=True)
            .order_by()
            .distinct()
        )
        collections = [c for c in collections if c]
        return "; ".join(collections)

    def observables_list(self):
        observables = (
            self.datasets.all_valid()
            .values_list("phenotype__observable__name", flat=True)
            .order_by()
            .distinct()
        )
        observables = [o for o in observables if o]
        return observables

    def observables_list_as_str(self):
        return "; ".join(self.observables_list())

    def phenotypes_aliases_list(self):

        datasets = self.datasets.all_valid()

        fields = [
            "phenotype__name",
            "phenotype__observable__name",
            "phenotype__reporter",
        ]

        all_names = list(datasets.values(*fields))

        aliases = []
        for f in fields:
            names = [d[f] for d in all_names]
            aliases += names

        aliases = list(set(aliases))
        aliases = [alias for alias in aliases if alias]
        return aliases

    def phenotypes_aliases_list_as_str(self):
        return "; ".join(self.phenotypes_aliases_list())

    def conditiontypes_list(self):
        conditiontypes = (
            self.datasets.values_list("conditionset__conditions__type__name", flat=True)
            .order_by()
            .distinct()
        )
        conditiontypes = [c for c in conditiontypes if c]
        return conditiontypes

    def conditiontypes_list_as_str(self):
        return "; ".join(self.conditiontypes_list())

    def conditions_aliases_list(self):

        datasets = self.datasets.all_valid()

        fields = [
            "conditionset__display_name",
            "conditionset__systematic_name",
            "conditionset__conditions__type__name",
            "conditionset__conditions__type__chebi_name",
            "conditionset__conditions__type__pubchem_name",
            "medium__display_name",
        ]

        all_names = list(datasets.values(*fields))

        aliases = []
        for f in fields:
            names = [d[f] for d in all_names]
            aliases += names

        aliases = list(set(aliases))
        aliases = [alias for alias in aliases if alias]
        return aliases

    def conditions_aliases_list_as_str(self):
        return "; ".join(self.conditions_aliases_list())

    def tags_list(self):

        tags = Tag.objects.all_valid()

        tags_list_self = Q(paper=self)
        tags_list_datasets = Q(dataset__paper=self) & Q(
            dataset__collection__is_valid=True
        )
        tags_list_conditionset = Q(conditionset__dataset__paper=self) & Q(
            conditionset__dataset__collection__is_valid=True
        )
        tags_list_condition = Q(condition__conditionset__dataset__paper=self) & Q(
            condition__conditionset__dataset__collection__is_valid=True
        )
        tags_list_conditiontype = Q(
            conditiontype__conditions__conditionset__dataset__paper=self
        ) & Q(
            conditiontype__conditions__conditionset__dataset__collection__is_valid=True
        )
        tags_list_medium = Q(medium__dataset__paper=self) & Q(
            medium__dataset__collection__is_valid=True
        )
        tags_list_phenotype = Q(phenotypes__dataset__paper=self) & Q(
            phenotypes__dataset__collection__is_valid=True
        )
        tags_list_observable = Q(observables__phenotype__dataset__paper=self) & Q(
            observables__phenotype__dataset__collection__is_valid=True
        )

        tags = tags.filter(
            tags_list_self
            | tags_list_datasets
            | tags_list_conditionset
            | tags_list_condition
            | tags_list_conditiontype
            | tags_list_medium
            | tags_list_phenotype
            | tags_list_observable
        )
        tags_list = list(tags.values_list("name", flat=True).order_by().distinct())
        return tags_list

    def tags_list_as_str(self):
        return "; ".join(self.tags_list())

    def tags_list_as_links(self):
        return mark_safe("; ".join([t.link_detail() for t in self.tags.all()]))

    def datasets_summary(self):
        str_list = [
            self.collections_list_as_str(),
            self.observables_summary,
            self.conditiontypes_summary,
        ]
        str_list = [s for s in str_list if s]
        return mark_safe("<br>".join(str_list))

    @property
    def datasets_number(self):
        return self.datasets.count()

    def acknowledgements_list_as_str(self):
        people = (
            self.datasets.values("data_source__label", "tested_source__label")
            .order_by()
            .distinct()
        )
        people = [list(person.values()) for person in people]
        people = list(set(list(itertools.chain.from_iterable(people))))
        people = [person for person in people if person]

        people2 = [person.split(',') for person in people]
        people2 = list(set(list(itertools.chain.from_iterable(people2))))
        people2 = [person.strip() for person in people2]

        return join_and(people2)

    def acknowledge_data(self):
        return self.datasets.filter(data_source__acknowledge=True).exists()

    def acknowledge_tested(self):
        return self.datasets.filter(tested_source__acknowledge=True).exists()

    def latest_data_status_name(self):
        if self.latest_data_status:
            return self.latest_data_status.status.name

    latest_data_status_name.admin_order_field = "latest_data_status__status__name"

    def latest_data_status_name_date(self):
        s = ""
        if self.latest_data_status:
            s = "%s (%s)" % (
                self.latest_data_status.status.name,
                self.latest_data_status.status_date,
            )
        return s

    latest_data_status_name_date.admin_order_field = "latest_data_status__status__name"

    def latest_tested_status_name(self):
        if self.latest_tested_status:
            return self.latest_tested_status.status.name

    latest_tested_status_name.admin_order_field = "latest_tested_status__status__name"

    def history(self):
        queryset_data = Statusdata.objects.filter(paper=self).order_by("status_date")
        queryset_tested = Statustested.objects.filter(paper=self).order_by(
            "status_date"
        )
        return {"data": queryset_data, "tested strains": queryset_tested}

    def link_detail(self):
        return mark_safe(
            '<a href="%s">%s</a>' % (reverse("papers:detail", args=(self.id,)), self)
        )

    def link_edit(self):
        html = '<a href="%s">%s</a>' % (
            reverse("admin:papers_paper_change", args=(self.id,)),
            self,
        )
        if self.latest_data_status and (
            self.latest_data_status.status_id == 10
        ):  # not relevant
            html = '<a href="%s" style="color: gray;">%s</a>' % (
                reverse("admin:papers_paper_change", args=(self.id,)),
                self,
            )
        return mark_safe(html)


class Statusdata(models.Model):
    paper = models.ForeignKey(Paper, on_delete=models.DO_NOTHING)
    status = models.ForeignKey(Status, on_delete=models.DO_NOTHING)
    status_date = models.DateField()

    class Meta:
        get_latest_by = "id"

    def __str__(self):
        return u"%s" % self.status


class Statustested(models.Model):
    paper = models.ForeignKey(Paper, on_delete=models.DO_NOTHING)
    status = models.ForeignKey(Status, on_delete=models.DO_NOTHING)
    status_date = models.DateField()

    class Meta:
        get_latest_by = "id"

    def __str__(self):
        return u"%s" % self.status
