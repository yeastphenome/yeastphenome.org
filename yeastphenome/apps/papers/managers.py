from django.apps import apps
from django.db import models
from django.db.models import Q

from yeastphenome.apps.tags.models import Tag
from yeastphenome.apps.common.utils import unique_clean_sorted

import pandas as pd


class PaperManager(models.Manager):
    def all_valid(self):
        papers = self.filter(latest_data_status__status__is_valid=True)
        papers = papers.filter(datasets__collection__is_valid=True).distinct()
        return papers

    def all_loaded(self):
        papers = self.all_valid()
        f = Q(latest_data_status__status__name__exact="loaded") & Q(
            latest_tested_status__status__name__in=[
                "loaded",
                "request abandoned",
                "not available",
            ]
        )
        papers = papers.filter(f)
        return papers

    def all_valid_as_df(self):

        # Prepare the following fields to be used by Elastic Search:
        # systematic_name, pmid, pub_date, data_abstract,
        # conditiontypes_summary, observables_summary
        # tags_list_as_str

        papers = self.all_valid().values("id",
                                         "systematic_name",
                                         "pmid",
                                         "pub_date",
                                         "data_abstract",
                                         "conditiontypes_summary",
                                         "observables_summary")
        papers_df = pd.DataFrame(list(papers))

        # Get the list of tags
        paper_tags = Tag.objects.all_mappings_as_df("papers", "paper")
        paper_tags.rename(columns={"tags_list": "self_tags_list"}, inplace=True)

        dataset_tags = apps.get_model("datasets", "Dataset").objects.all_valid_tags_list_as_df()
        paper2datasets = dataset_tags.groupby("paper_id").agg({"tags_list": "sum"}).reset_index()
        paper2datasets.rename(columns={"paper_id": "id", "tags_list": "related_tags_list"}, inplace=True)

        paper_tags = paper_tags.merge(paper2datasets, how="outer", on="id")
        for f in ["self_tags_list", "related_tags_list"]:
            paper_tags[f] = paper_tags[f].apply(lambda x: x if isinstance(x, list) else [])

        columns = ["self_tags_list", "related_tags_list"]
        paper_tags["tags_list"] = paper_tags[columns].apply(unique_clean_sorted, axis=1)

        papers_df = papers_df.merge(paper_tags[["id", "tags_list"]], how="left", on="id")
        papers_df["tags_list"] = papers_df["tags_list"].apply(lambda x: x if isinstance(x, list) else [])
        papers_df["tags_list_as_str"] = papers_df["tags_list"].apply(lambda x: "; ".join(x))

        columns = ["id",
                   "systematic_name",
                   "pmid",
                   "pub_date",
                   "data_abstract",
                   "conditiontypes_summary",
                   "observables_summary",
                   "tags_list_as_str"]
        return papers_df[columns]
