from django.db.models import Q, F

from yeastphenome.apps.papers.models import Paper
from yeastphenome.apps.conditions.models import ConditionType
from yeastphenome.apps.phenotypes.models import Observable
from yeastphenome.apps.datasets.models import Dataset
from yeastphenome.apps.genes.models import Gene


def escape_regex(value):
    """To use iregex in a search, if regular expression characters are included,
    we need to search for them verbatim. This function should replace them with
    an escape character.
    """
    for char in ["(", ")", "[", "]", "?"]:
        value = value.replace(char, "\%s" % char)
    return value


def get_latest_stats_basic():

    conditions_qs = ConditionType.objects.all_valid()
    datasets_qs = Dataset.objects.all_valid()
    genes_qs = Gene.objects.all_valid()
    papers_qs = Paper.objects.all_valid()
    phenotypes_qs = Observable.objects.all_valid()

    papers_nr = papers_qs.count()
    phenotypes_nr = phenotypes_qs.count()
    conditions_nr = conditions_qs.count()
    datasets_nr = datasets_qs.count()
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
    papers_processed_qs = Paper.objects.all_loaded()

    # phenotypes_qs = Phenotype.objects.all_valid()
    # conditions_qs = ConditionSet.objects.all_valid()
    # conditiontypes_qs = ConditionType.objects.all_valid()

    datasets_qs = Dataset.objects.all_loaded()
    genes_qs = Gene.objects.all_valid()

    # Total number of papers to process
    papers_nr = papers_qs.count()
    genes_nr = genes_qs.count()

    # Number of hopeless papers
    f = Q(latest_data_status__status__name__in=["request abandoned", "not available"])
    papers_hopeless_nr = papers_qs.filter(f).count()
    papers_hopeful_nr = papers_nr - papers_hopeless_nr

    # Number of labs
    labs_nr = papers_qs.values("last_author").order_by().distinct().count()

    # Number of papers processed and loaded
    papers_processed_nr = papers_processed_qs.count()

    # Number of phenotypes
    phenotypes_nr = papers_processed_qs.values("datasets__phenotype").distinct().count()

    # Number of conditions
    conditions_nr = (
        papers_processed_qs.values("datasets__conditionset").distinct().count()
    )

    # Number of datasets
    datasets_nr = datasets_qs.count()

    # Data recovery for haploid/homozygous diploid
    g1 = Q(
        data_measured__rank__lt=F("data_published__rank")
    )  # datasets in need of data recovery
    g2 = Q(
        data_available__rank__lt=F("data_published__rank")
    )  # datasets with recovered data

    h1 = Q(tested_list_published=False)  # datasets in need of tested list recovery
    h2 = Q(tested_list_published=False) & Q(
        tested_source_id__isnull=False
    )  # datasets with recovered tested list

    datasets_nr_need_data = datasets_qs.filter(g1).distinct().count()
    datasets_nr_recovered_data = datasets_qs.filter(g2).distinct().count()

    datasets_nr_need_tested = datasets_qs.filter(h1).distinct().count()
    datasets_nr_recovered_tested = datasets_qs.filter(h2).distinct().count()

    datasets_nr_recovered_any = datasets_qs.filter(g2 | h2).distinct().count()

    # Collection type and data modalities
    c1 = Q(collection__shortname__in=["hap a", "hap a (post-SGA)"])
    c2 = Q(collection__shortname__in=["hap alpha", "hap alpha (post-SGA)"])
    c3 = Q(collection__shortname__in=["hom"])
    c5 = Q(
        collection__shortname__in=[
            "hap ?",
            "hap a/hap alpha/hom",
            "hap a/hap alpha",
            "hap a/hom",
        ]
    )
    d1 = Q(data_available__shortname="q")
    d2 = Q(data_available__shortname="qofh")
    d3 = Q(data_available__shortname="d")

    collectiontype_datatype = dict()
    collectiontype_datatype["total"] = 0
    for ic, c in enumerate([c1, c2, c3, c5]):
        nr = datasets_qs.filter(c).count()
        label = "c" + str(ic)
        collectiontype_datatype[label] = nr
        collectiontype_datatype["total"] += nr
        for id, d in enumerate([d1, d2, d3]):
            if ic == 0:
                nr = datasets_qs.filter(d).count()
                label = "d" + str(id)
                collectiontype_datatype[label] = nr
            nr = datasets_qs.filter(c & d).count()
            label = "c" + str(ic) + "d" + str(id)
            collectiontype_datatype[label] = nr

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

    # --- Phenotypes ----
    p1 = Q(phenotype__name__contains="growth")
    p2 = Q(phenotype__name__contains="expression of")
    p3 = ~Q(phenotype__name__contains="growth") & ~Q(
        phenotype__name__contains="expression of"
    )

    collectiontype_phenotype = dict()
    collectiontype_phenotype["total"] = 0
    for ic, c in enumerate([c1, c2, c3, c5]):
        nr = datasets_qs.filter(c).count()
        label = "c" + str(ic)
        collectiontype_phenotype[label] = nr
        collectiontype_phenotype["total"] += nr
        for ip, p in enumerate([p1, p2, p3]):
            if ic == 0:
                nr = datasets_qs.filter(p).count()
                label = "p" + str(ip)
                collectiontype_phenotype[label] = nr
            nr = datasets_qs.filter(c & p).count()
            label = "c" + str(ic) + "p" + str(ip)
            collectiontype_phenotype[label] = nr

    context = {
        "papers_nr": papers_nr,
        "papers_hopeless_nr": papers_hopeless_nr,
        "papers_hopeful_nr": papers_hopeful_nr,
        "papers_processed_nr": papers_processed_nr,
        "genes_nr": genes_nr,
        "labs_nr": labs_nr,
        "phenotypes_nr": phenotypes_nr,
        "conditions_nr": conditions_nr,
        "datasets_nr": datasets_nr,
        "datasets_nr_recovered_any": datasets_nr_recovered_any,
        "datasets_nr_need_data": datasets_nr_need_data,
        "datasets_nr_need_tested": datasets_nr_need_tested,
        "datasets_nr_recovered_data": datasets_nr_recovered_data,
        "datasets_nr_recovered_tested": datasets_nr_recovered_tested,
        "collectiontype_datatype": collectiontype_datatype,
        "collectiontype_phenotype": collectiontype_phenotype,
    }

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
