from django.db.models import Q, F, Count, Sum, Case, When
from django.db import models

import numpy as np

from yeastphenome import settings
from yeastphenome.apps.papers.models import Paper
from yeastphenome.apps.conditions.models import ConditionSet, ConditionType
from yeastphenome.apps.phenotypes.models import Phenotype, Measurement
from yeastphenome.apps.datasets.models import Dataset, Sourcetype
from yeastphenome.apps.genes.models import Gene

import collections


# Search


def escape_regex(value):
    """To use iregex in a search, if regular expression characters are included,
    we need to search for them verbatim. This function should replace them with
    an escape character.
    """
    for char in ["(", ")", "[", "]", "?"]:
        value = value.replace(char, "\%s" % char)
    return value


# Downloads


def check_download_space(request, datasets):
    """The browser can only serialize 4096 bytes of cookies, so we cannot allow
    the cart to exceed this number. We have some wiggle room because the session
    is compressed, so we calculated 500 datasets (the list of ids) can go right
    up to the limit. If other session data is added, this would need to be
    decreased. Returns False if the cart cannot be added to, True otherwise
    """
    datasets_in_cart = len(request.session["cart"])
    if datasets_in_cart + len(datasets) > settings.DOWNLOAD_CART_LIMIT:
        return False
    return True


# Phenotypes


def get_phenotype_measurements(hide_legend=False):
    """Return a breakdown of phenotypes according to what they measure.
    Most of these are undefined, but it might be useful to see those
    that are.
    """
    undefined = 0
    counts = {}
    for phenotype in Phenotype.objects.all():
        if phenotype.measurement is None:
            undefined += 1
        else:
            if phenotype.measurement.name not in counts:
                counts[phenotype.measurement.name] = 0
            counts[phenotype.measurement.name] += 1

    return {
        "hide_legend": hide_legend,
        "phenotype_measurements": counts,
        "phenotype_measurements_undefined": undefined,
        "measurements": Measurement.objects.all(),
    }


# Collections change over time


def get_collections_by_year(collection):
    """Show the change over time of a collection tyoe. This function returns
    a lookup with single values, and also accumulated values.
    This graph displays on a page for a single dataset. There is only one
    dataset without a collection, and it was published in 2015 (and this
    will return that one number).
    """
    counts = {}
    for dataset in Dataset.objects.filter(collection=collection):
        if dataset.paper.pub_date not in counts:
            counts[dataset.paper.pub_date] = 0
        counts[dataset.paper.pub_date] += 1

    # Order by year before summing
    counts = collections.OrderedDict(sorted(counts.items()))

    # Generate accumulated counts
    total = 0
    summed = {}
    for year, count in counts.items():
        total += count
        summed[year] = total
    return {"summed": summed, "counts": counts}


# Datasets


def get_dataset_sources():
    """generate data to render into a graph for data set sources"""
    sourcetypes = [x["name"] for x in Sourcetype.objects.values("name").distinct()]
    counts = {}
    for sourcetype in sourcetypes:
        counts[sourcetype] = Dataset.objects.filter(
            data_source__sourcetype__name=sourcetype
        ).count()
    return {"dataset_sources_counts": counts}


# Stats helper function

def get_latest_stats_basic():

    papers_qs = Paper.objects.all_valid()
    papers_nr = papers_qs.count()

    genes_qs = Gene.objects.all_valid()

    # Number of papers processed and loaded
    f = Q(latest_data_status__status__name__exact="loaded") & Q(
        latest_tested_status__status__name__in=[
            "loaded",
            "request abandoned",
            "not available",
        ]
    )
    papers_processed_qs = papers_qs.filter(f)
    papers_processed_nr = papers_processed_qs.count()

    # Number of phenotypes
    phenotypes_nr = papers_processed_qs.values("datasets__phenotype").distinct().count()

    # Number of conditions
    conditions_nr = papers_processed_qs.values("datasets__conditionset").distinct().count()

    # Number of datasets
    datasets_nr = papers_processed_qs.values("datasets").distinct().count()

    # Number of genes
    genes_nr = genes_qs.count()

    context = {
        "papers_nr": papers_nr,
        "phenotypes_nr": phenotypes_nr,
        "conditions_nr": conditions_nr,
        "datasets_nr": datasets_nr,
        "genes_nr": genes_nr,
    }

    return context


def get_latest_stats():
    """Return number of papers, phenotypes, and datasets to display in the index
    view. If no entries are found, display counts of zero.
    """
    papers_qs = Paper.objects.all_valid()
    phenotypes_qs = Phenotype.objects.all_valid()
    conditions_qs = ConditionSet.objects.all_valid()
    conditiontypes_qs = ConditionType.objects.all_valid()
    datasets_qs = Dataset.objects.all_valid()
    genes_qs = Gene.objects.all_valid()

    # Total number of papers to process
    # f = Q(latest_data_status__status__is_valid=True)
    papers_nr = papers_qs.count()
    genes_nr = genes_qs.count()

    # # Latest modified paper
    # updated_on = papers_qs.latest().modified_on
    #
    # Number of hopeless papers
    f = Q(latest_data_status__status__name__in=["request abandoned", "not available"])
    papers_hopeless_nr = papers_qs.filter(f).count()

    # Number of labs
    labs_nr = papers_qs.values("last_author").distinct().count()

    # Number of papers processed and loaded
    f = Q(latest_data_status__status__name__exact="loaded") & Q(
        latest_tested_status__status__name__in=[
            "loaded",
            "request abandoned",
            "not available",
        ]
    )
    papers_processed_qs = papers_qs.filter(f)
    papers_processed_nr = papers_processed_qs.count()

    # Number of phenotypes
    phenotypes_nr = papers_processed_qs.values("datasets__phenotype").distinct().count()

    # Number of conditions
    conditions_nr = papers_processed_qs.values("datasets__conditionset").distinct().count()

    # Number of datasets
    datasets_nr = papers_processed_qs.values("datasets").distinct().count()

    # # --- Conditions ---
    # top_conditiontypes = (
    #     conditiontypes_qs.annotate(
    #         nr_papers=Count("condition__conditionset__dataset__paper", distinct=True)
    #     )
    #     .annotate(
    #         nr_datasets=Sum(
    #             Case(
    #                 When(
    #                     condition__conditionset__dataset__data_available__shortname__in=[
    #                         "q",
    #                         "qofh",
    #                         "d",
    #                     ],
    #                     then=1,
    #                 ),
    #                 default=0,
    #                 output_field=models.IntegerField(),
    #             )
    #         ),
    #         nr_datasets_q=Sum(
    #             Case(
    #                 When(
    #                     condition__conditionset__dataset__data_available__shortname="q",
    #                     then=1,
    #                 ),
    #                 default=0,
    #                 output_field=models.IntegerField(),
    #             )
    #         ),
    #         nr_datasets_d=Sum(
    #             Case(
    #                 When(
    #                     condition__conditionset__dataset__data_available__shortname="d",
    #                     then=1,
    #                 ),
    #                 default=0,
    #                 output_field=models.IntegerField(),
    #             )
    #         ),
    #         nr_datasets_qofh=Sum(
    #             Case(
    #                 When(
    #                     condition__conditionset__dataset__data_available__shortname="qofh",
    #                     then=1,
    #                 ),
    #                 default=0,
    #                 output_field=models.IntegerField(),
    #             )
    #         ),
    #     )
    #     .exclude(name__in=["standard", "time"])
    #     .order_by("-nr_papers")
    # )
    #
    # # top_conditiontypes_q = top_conditiontypes. \
    # #     annotate(nr_datasets_q=Count(condition__conditionset__dataset__paper__data_available__shortname='q'))
    #
    # # --- Phenotypes ----
    # p = Q(paper__in=papers_processed_qs)
    # c1 = Q(
    #     collection__shortname__in=[
    #         "hap a",
    #         "hap a (post-SGA)",
    #         "hap alpha",
    #         "hap alpha (post-SGA)",
    #         "hom",
    #         "hap ?",
    #         "hap a/hap alpha/hom",
    #         "hap a/hap alpha",
    #         "hap a/hom",
    #     ]
    # )
    # c2 = Q(collection__shortname__in=["het"])
    # gr = Q(phenotype__name__contains="growth")
    # exp = Q(phenotype__name__contains="gene expression")
    # datasets_processed_homhap_qs = datasets_qs.filter(p & c1)
    # datasets_processed_het_qs = datasets_qs.filter(p & c2)
    #
    # datasets_nr_processed_homhap = datasets_processed_homhap_qs.count()
    # papers_nr_processed_homhap = (
    #     datasets_processed_homhap_qs.values("paper_id").distinct().count()
    # )
    #
    # datasets_nr_processed_het = datasets_processed_het_qs.count()
    # papers_nr_processed_het = (
    #     datasets_processed_het_qs.values("paper_id").distinct().count()
    # )
    #
    # datasets_nr_processed_homhap_growth = datasets_processed_homhap_qs.filter(
    #     gr
    # ).count()
    # papers_nr_processed_homhap_growth = (
    #     datasets_processed_homhap_qs.filter(gr).values("paper_id").distinct().count()
    # )
    #
    # datasets_nr_processed_het_growth = datasets_processed_het_qs.filter(gr).count()
    # papers_nr_processed_het_growth = (
    #     datasets_processed_het_qs.filter(gr).values("paper_id").distinct().count()
    # )
    #
    # datasets_nr_processed_homhap_expression = datasets_processed_homhap_qs.filter(
    #     exp
    # ).count()
    # papers_nr_processed_homhap_expression = (
    #     datasets_processed_homhap_qs.filter(exp).values("paper_id").distinct().count()
    # )
    #
    # datasets_nr_processed_het_expression = datasets_processed_het_qs.filter(exp).count()
    # papers_nr_processed_het_expression = (
    #     datasets_processed_het_qs.filter(exp).values("paper_id").distinct().count()
    # )
    #
    # datasets_nr_processed_homhap_other = (
    #     datasets_processed_homhap_qs.exclude(gr).exclude(exp).count()
    # )
    # papers_nr_processed_homhap_other = (
    #     datasets_processed_homhap_qs.exclude(gr)
    #     .exclude(exp)
    #     .values("paper_id")
    #     .distinct()
    #     .count()
    # )
    #
    # datasets_nr_processed_het_other = (
    #     datasets_processed_het_qs.exclude(gr).exclude(exp).count()
    # )
    # papers_nr_processed_het_other = (
    #     datasets_processed_het_qs.exclude(gr)
    #     .exclude(exp)
    #     .values("paper_id")
    #     .distinct()
    #     .count()
    # )
    #
    # # --- Collections ----
    # f = Q(paper__in=papers_processed_qs)
    #
    # c = Q(collection__shortname__in=["hap a", "hap a (post-SGA)"])
    # datasets_nr_hap_a = datasets_qs.filter(f & c).distinct().count()
    # datasets_prc_hap_a = (
    #     int(np.rint(100 * datasets_nr_hap_a / datasets_nr)) if datasets_nr != 0 else 0
    # )
    #
    # c = Q(collection__shortname__in=["hap alpha", "hap alpha (post-SGA)"])
    # datasets_nr_hap_alpha = datasets_qs.filter(f & c).distinct().count()
    # datasets_prc_hap_alpha = (
    #     int(np.rint(100 * datasets_nr_hap_alpha / datasets_nr))
    #     if datasets_nr != 0
    #     else 0
    # )
    #
    # c = Q(collection__shortname__in=["hom"])
    # datasets_nr_hom = datasets_qs.filter(f & c).distinct().count()
    # datasets_prc_hom = (
    #     int(np.rint(100 * datasets_nr_hom / datasets_nr)) if datasets_nr != 0 else 0
    # )
    #
    # c = Q(collection__shortname__in=["het"])
    # datasets_nr_het = datasets_qs.filter(f & c).distinct().count()
    # datasets_prc_het = (
    #     int(np.rint(100 * datasets_nr_het / datasets_nr)) if datasets_nr != 0 else 0
    # )
    #
    # c = Q(
    #     collection__shortname__in=[
    #         "hap ?",
    #         "hap a/hap alpha/hom",
    #         "hap a/hap alpha",
    #         "hap a/hom",
    #         "hom/het?",
    #         "hom/het",
    #         "hap a/het",
    #         "hap ?/hom/het",
    #     ]
    # )
    # datasets_nr_mix = datasets_qs.filter(f & c).distinct().count()
    # datasets_prc_mix = (
    #     int(np.rint(100 * datasets_nr_mix / datasets_nr)) if datasets_nr != 0 else 0
    # )
    #
    # datasets_nr_collections_total = (
    #     datasets_nr_hap_a
    #     + datasets_nr_hap_alpha
    #     + datasets_nr_hom
    #     + datasets_nr_het
    #     + datasets_nr_mix
    # )
    #
    # # c = Q(collection__shortname__in=['hap a', 'hap alpha', 'hom', 'het', 'hap ?', 'hap a/hap alpha/hom',
    # #                                  'hap a/hap alpha', 'hap a/hom', 'hom/het?',
    # #                                  'hom/het', 'hap a/het', 'hap ?/hom/het'])
    # # missing = datasets_queryset.filter(f).exclude(c)
    #
    # # --- Data types ---
    # f = Q(paper__in=papers_processed_qs) & Q(data_available__shortname="q")
    # datasets_nr_q = datasets_qs.filter(f).distinct().count()
    # datasets_prc_q = (
    #     int(np.rint(100 * datasets_nr_q / datasets_nr)) if datasets_nr != 0 else 0
    # )
    #
    # f = Q(paper__in=papers_processed_qs) & Q(data_available__shortname="qofh")
    # datasets_nr_qofh = datasets_qs.filter(f).distinct().count()
    # datasets_prc_qofh = (
    #     int(np.rint(100 * datasets_nr_qofh / datasets_nr)) if datasets_nr != 0 else 0
    # )
    #
    # f = Q(paper__in=papers_processed_qs) & Q(data_available__shortname="d")
    # datasets_nr_d = datasets_qs.filter(f).distinct().count()
    # datasets_prc_d = (
    #     int(np.rint(100 * datasets_nr_d / datasets_nr)) if datasets_nr != 0 else 0
    # )
    #
    # datasets_nr_data_available_total = datasets_nr_q + datasets_nr_qofh + datasets_nr_d
    #
    # # Data recovery for haploid/homozygous diploid
    # f = Q(paper__in=papers_processed_qs)
    #
    # g1 = Q(
    #     data_measured__rank__lt=F("data_published__rank")
    # )  # papers in need of data recovery
    # g2 = Q(
    #     data_available__rank__lt=F("data_published__rank")
    # )  # papers with recovered data
    #
    # h1 = Q(tested_list_published=False)  # papers in need of tested list recovery
    # h2 = Q(tested_list_published=False) & Q(
    #     tested_source_id__isnull=False
    # )  # papers with recovered tested list
    #
    # fgh = f & (g2 | h2)  # all papers with something recovered
    #
    # datasets_nr_need_data = datasets_qs.filter(f & g1).distinct().count()
    # datasets_nr_need_tested = datasets_qs.filter(f & h1).distinct().count()
    #
    # datasets_nr_recovered_all = datasets_qs.filter(fgh).distinct().count()
    # datasets_nr_recovered_data = datasets_qs.filter(f & g2).distinct().count()
    # datasets_nr_recovered_tested = datasets_qs.filter(f & h2).distinct().count()
    #

    context = {
        "papers_nr": papers_nr,
        "genes_nr": genes_nr,
        "papers_hopeless_nr": papers_hopeless_nr,
        "labs_nr": labs_nr,
        "papers_processed_nr": papers_processed_nr,
        "phenotypes_nr": phenotypes_nr,
        "conditions_nr": conditions_nr,
        "datasets_nr": datasets_nr
    }
    #     "datasets_nr_hap_a": datasets_nr_hap_a,
    #     "datasets_prc_hap_a": datasets_prc_hap_a,
    #     "datasets_nr_hap_alpha": datasets_nr_hap_alpha,
    #     "datasets_prc_hap_alpha": datasets_prc_hap_alpha,
    #     "datasets_nr_hom": datasets_nr_hom,
    #     "datasets_prc_hom": datasets_prc_hom,
    #     "datasets_nr_het": datasets_nr_het,
    #     "datasets_prc_het": datasets_prc_het,
    #     "datasets_nr_mix": datasets_nr_mix,
    #     "datasets_prc_mix": datasets_prc_mix,
    #     "datasets_nr_collections_total": datasets_nr_collections_total,
    #     "datasets_nr_q": datasets_nr_q,
    #     "datasets_prc_q": datasets_prc_q,
    #     "datasets_nr_qofh": datasets_nr_qofh,
    #     "datasets_prc_qofh": datasets_prc_qofh,
    #     "datasets_nr_d": datasets_nr_d,
    #     "datasets_prc_d": datasets_prc_d,
    #     "datasets_nr_data_available_total": datasets_nr_data_available_total,
    #     "datasets_nr_need_data": datasets_nr_need_data,
    #     "datasets_nr_need_tested": datasets_nr_need_tested,
    #     "datasets_nr_recovered_all": datasets_nr_recovered_all,
    #     "datasets_nr_recovered_data": datasets_nr_recovered_data,
    #     "datasets_nr_recovered_tested": datasets_nr_recovered_tested,
    #     "top_conditiontypes": top_conditiontypes[:10],
    #     "datasets_nr_processed_homhap": datasets_nr_processed_homhap,
    #     "datasets_nr_processed_homhap_growth": datasets_nr_processed_homhap_growth,
    #     "datasets_nr_processed_homhap_expression": datasets_nr_processed_homhap_expression,
    #     "datasets_nr_processed_homhap_other": datasets_nr_processed_homhap_other,
    #     "papers_nr_processed_homhap": papers_nr_processed_homhap,
    #     "papers_nr_processed_homhap_growth": papers_nr_processed_homhap_growth,
    #     "papers_nr_processed_homhap_expression": papers_nr_processed_homhap_expression,
    #     "papers_nr_processed_homhap_other": papers_nr_processed_homhap_other,
    #     "datasets_nr_processed_het": datasets_nr_processed_het,
    #     "datasets_nr_processed_het_growth": datasets_nr_processed_het_growth,
    #     "datasets_nr_processed_het_expression": datasets_nr_processed_het_expression,
    #     "datasets_nr_processed_het_other": datasets_nr_processed_het_other,
    #     "papers_nr_processed_het": papers_nr_processed_het,
    #     "papers_nr_processed_het_growth": papers_nr_processed_het_growth,
    #     "papers_nr_processed_het_expression": papers_nr_processed_het_expression,
    #     "papers_nr_processed_het_other": papers_nr_processed_het_other,
    #     "updated_on": updated_on,
    # }

    return context
