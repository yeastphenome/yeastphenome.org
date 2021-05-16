from django.db import models
from django.db.models.functions import Lower
from django.urls import reverse
from django.db.models import Q
from django.conf import settings
from django.contrib.auth.models import User
from django.utils.safestring import mark_safe

from yeastphenome.apps.phenotypes.models import Observable
from yeastphenome.apps.conditions.models import ConditionType
from yeastphenome.apps.datasets.models import Collection, Source
from yeastphenome.apps.tags.models import Tag
from yeastphenome.apps.common.utils_format import truncated_list_as_str

import os


class Status(models.Model):
    name = models.CharField(max_length=200, default="undefined", blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    is_valid = models.BooleanField()

    def __str__(self):
        return u"%s" % self.name

    class Meta:
        ordering = ["name"]


class PaperManager(models.Manager):

    def all_valid(self):
        # Valid = is relevant
        return self.exclude(latest_data_status__status__name__in=["not relevant", "undefined"])


class Paper(models.Model):
    first_author = models.CharField(max_length=200)
    last_author = models.CharField(max_length=200, blank=True, null=True)
    pub_date = models.IntegerField(default=0)
    systematic_name = models.CharField(max_length=200, blank=False, null=False)

    pmid = models.IntegerField(default=0)
    notes = models.TextField(blank=True)
    private_notes = models.TextField(blank=True)
    data_abstract = models.TextField(blank=True, null=True)

    user = models.ForeignKey(User, blank=True, null=True, on_delete=models.DO_NOTHING)
    tags = models.ManyToManyField(Tag, blank=True)

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
        return self.systematic_name

    def collections_list_as_str(self):
        collections = self.datasets.values_list("collection__shortname", flat=True).order_by().distinct()
        return "; ".join(collections)

    # def phenotypes(self):
    #     return (
    #         Observable.objects.filter(phenotype__dataset__paper=self)
    #         .distinct()
    #         .order_by(Lower("name"))
    #     )

    def phenotypes_list_as_str(self):
        phenotypes = self.datasets.values_list("phenotype__observable__name", flat=True).order_by().distinct()
        return truncated_list_as_str(phenotypes)

    # def conditiontypes(self):
    #     return ConditionType.objects.filter(
    #         conditions__conditionset__dataset__paper=self
    #     ).distinct()

    def conditiontypes_list_as_str(self):
        conditiontypes = self.datasets.values_list("conditionset__conditions__type__name", flat=True).order_by().distinct()
        return truncated_list_as_str(conditiontypes)

    def datasets_summary(self):
        str_list = [self.collections_list_as_str(), self.phenotypes_list_as_str(), self.conditiontypes_list_as_str()]
        return mark_safe("<br>".join(str_list))

    @property
    def datasets_number(self):
        return self.datasets.count()

    def should_have_data(self):
        # Returns True if data has been loaded from data files
        return self.latest_data_status and "loaded" == str(
            self.latest_data_status.status.name
        )

    def raw_available_data(self):
        # Returns True if it should have data, and has access to raw data
        return self.should_have_data() and self.download_path_exists

    def download_path(self):
        # Returns a path of where datafiles should be, regardless if it has data files or not
        return os.path.join(settings.DATA_DIR, str(self.pmid))

    @property
    def download_path_exists(self):
        # Regardless if the paper should have data, returns True or False if there is a data directory for this paper
        return os.path.isdir(self.download_path())

    def static_dir_name(self):
        return "%s_%s~%s" % (
            self.pub_date,
            self.first_author.split(" ")[0],
            self.last_author.split(" ")[0],
        )

    def acknowledgements_str_list(self):
        return ", ".join(
            Source.objects.filter(acknowledge=True)
            .filter(Q(data_source__paper=self) | Q(tested_source__paper=self))
            .exclude(Q(person=None))
            .values_list("person", flat=True)
            .distinct()
        )

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
        return mark_safe('<a href="%s">%s</a>' % (self.get_absolute_url(), self))

    def get_absolute_url(self):
        return reverse("papers:detail", args=(self.id,))

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
