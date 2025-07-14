from django.db import models
from django.apps import apps
from django.db.models import Q

from yeastphenome.apps.common.utils import unique_clean_sorted
from yeastphenome.apps.tags.models import Tag

import itertools


class CollectionManager(models.Manager):
    def all_valid(self):
        # Valid = associated with at least 1 dataset from a relevant paper
        valid_collections = apps.get_model("datasets", "Dataset").objects.all_valid().values("collection").distinct()
        return self.filter(pk__in=valid_collections)


class SourceManager(models.Manager):

    def all_valid(self):
        valid_datasets = apps.get_model("datasets", "Dataset").objects.all_valid()
        return (
            self.filter(
                Q(data_source__in=valid_datasets) | Q(tested_source__in=valid_datasets)
            )
            .order_by()
            .distinct()
        )

    def people_to_acknowledge(self):
        valid_datasets = apps.get_model("datasets", "Dataset").objects.all_valid()
        sources = self.filter(sourcetype_id=5).filter(acknowledge=True).filter(release=True)
        sources = (
            sources.filter(
                Q(data_source__in=valid_datasets) | Q(tested_source__in=valid_datasets)
            )
            .order_by()
            .distinct()
        )
        people_list = sources.values_list("label", flat=True)
        people_list = [person.split(", ") for person in people_list]
        people_list = list(set(itertools.chain.from_iterable(people_list)))
        people_list = [
            person for person in people_list if person not in [None, "", "Anastasia Baryshnikova"]
        ]
        return people_list


class DatasetManager(models.Manager):

    def all_valid(self):
        datasets = self.filter(paper__latest_data_status__status__is_valid=True)
        datasets = datasets.filter(collection__is_valid=True)
        return datasets

    def all_loaded(self):
        datasets = self.all_valid()
        f = Q(paper__latest_data_status__status__name__exact="loaded") & Q(
            paper__latest_tested_status__status__name__in=[
                "loaded",
                "request abandoned",
                "not available",
            ]
        )
        datasets = datasets.filter(f)
        return datasets

    def all_valid_tags_list_as_df(self):

        import pandas as pd

        datasets = self.all_valid().values("id", "paper", "phenotype", "conditionset", "medium")
        datasets_df = pd.DataFrame(list(datasets))
        datasets_df.rename(columns={"paper": "paper_id",
                                    "phenotype": "phenotype_id",
                                    "conditionset": "conditionset_id",
                                    "medium": "medium_id"}, inplace=True)

        dataset_tags = Tag.objects.all_mappings_as_df("datasets", "Dataset")
        dataset_tags.rename(columns={"tags_list": "dataset_tags_list"}, inplace=True)

        phenotype_tags = apps.get_model("phenotypes", "Phenotype").objects.all_valid_tags_list_as_df()
        phenotype_tags.rename(columns={"tags_list": "phenotype_tags_list"}, inplace=True)

        conditionset_tags = apps.get_model("conditions", "ConditionSet").objects.all_valid_tags_list_as_df()
        conditionset_tags.rename(columns={"tags_list": "conditionset_tags_list"}, inplace=True)

        medium_tags = apps.get_model("conditions", "Medium").objects.all_valid_tags_list_as_df()
        medium_tags.rename(columns={"tags_list": "medium_tags_list"}, inplace=True)

        # Merge all tags into the main DataFrame
        datasets_df = datasets_df.merge(dataset_tags[["id", "dataset_tags_list"]], how="left", on="id")
        datasets_df["dataset_tags_list"] = \
            datasets_df["dataset_tags_list"].apply(lambda x: x if isinstance(x, list) else [])

        datasets_df = datasets_df.merge(phenotype_tags[["id", "phenotype_tags_list"]],
                                        how="left", left_on="phenotype_id", right_on="id")
        datasets_df.rename(columns={"id_x": "id"}, inplace=True)
        datasets_df["phenotype_tags_list"] = \
            datasets_df["phenotype_tags_list"].apply(lambda x: x if isinstance(x, list) else [])

        datasets_df = datasets_df.merge(conditionset_tags[["id", "conditionset_tags_list"]],
                                        how="left", left_on="conditionset_id", right_on="id")
        datasets_df.rename(columns={"id_x": "id"}, inplace=True)
        datasets_df["conditionset_tags_list"] = \
            datasets_df["conditionset_tags_list"].apply(lambda x: x if isinstance(x, list) else [])

        datasets_df = datasets_df.merge(medium_tags[["id", "medium_tags_list"]],
                                        how="left", left_on="medium_id", right_on="id")
        datasets_df.rename(columns={"id_x": "id"}, inplace=True)
        datasets_df["medium_tags_list"] = \
            datasets_df["medium_tags_list"].apply(lambda x: x if isinstance(x, list) else [])

        columns = ["dataset_tags_list", "phenotype_tags_list", "conditionset_tags_list", "medium_tags_list"]
        datasets_df["tags_list"] = datasets_df[columns].apply(unique_clean_sorted, axis=1)
        datasets_df["tags_list_as_str"] = datasets_df["tags_list"].apply(lambda x: "; ".join(x))

        columns = ["id", "paper_id", "tags_list", "tags_list_as_str"]
        return datasets_df[columns]

    def all_valid_as_df(self):

        import pandas as pd

        # Prepare the following fields to be used by Elastic Search:
        # id, paper, collection, data_available,
        # medium, conditionset, conditions_aliases_list_as_str,
        # phenotype,
        # conditions, medium, tags_list_as_str

        datasets = self.all_valid().values("id",
                                           "paper__systematic_name",
                                           "collection__shortname",
                                           "data_available__name",
                                           "conditionset",
                                           "medium__display_name",
                                           "phenotype",
                                           )
        datasets_df = pd.DataFrame(list(datasets))
        datasets_df.columns = ["id",
                               "paper",
                               "collection",
                               "data_available",
                               "conditionset_id",
                               "medium",
                               "phenotype_id"]

        # Get the list of condition aliases
        conditionset_aliases = apps.get_model("conditions", "ConditionSet").objects.all_valid_aliases_list_as_df()
        datasets_df = datasets_df.merge(conditionset_aliases[["id", "display_name", "aliases_list_as_str"]],
                                        how="left", left_on="conditionset_id", right_on="id")
        datasets_df.rename(columns={"id_x": "id",
                                    "display_name": "conditionset",
                                    "aliases_list_as_str": "conditionset_aliases_list_as_str"},
                           inplace=True)

        # Get the list of phenotype aliases
        phenotype_aliases = apps.get_model("phenotypes", "Phenotype").objects.all_valid_aliases_list_as_df()
        datasets_df = datasets_df.merge(phenotype_aliases[["id", "name", "aliases_list_as_str"]],
                                        how="left", left_on="phenotype_id", right_on="id")
        datasets_df.rename(columns={"id_x": "id",
                                    "name": "phenotype",
                                    "aliases_list_as_str": "phenotype_aliases_list_as_str"},
                           inplace=True)

        # Get the list of tags
        dataset_tags = self.all_valid_tags_list_as_df()
        datasets_df = datasets_df.merge(dataset_tags, how="left", on="id")

        columns = ["id",
                   "paper",
                   "collection",
                   "data_available",
                   "medium",
                   "conditionset",
                   "conditionset_aliases_list_as_str",
                   "phenotype",
                   "phenotype_aliases_list_as_str",
                   "tags_list_as_str"]
        return datasets_df[columns]


class DataManager(models.Manager):
    def all_valid(self):
        valid_datasets = apps.get_model("datasets", "Dataset").objects.all_valid()
        return self.filter(dataset__in=valid_datasets)