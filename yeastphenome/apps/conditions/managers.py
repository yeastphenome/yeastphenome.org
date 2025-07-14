from django.apps import apps
from django.db import models, connection
from django.db.models import Q

from yeastphenome.apps.common.utils import unique_clean_sorted
from yeastphenome.apps.tags.models import Tag


class ConditionTypeManager(models.Manager):

    def all_valid(self):
        valid_datasets = apps.get_model("datasets", "Dataset").objects.all_valid()
        # Note: not including conditiontypes used in Medium because they are too generic (e.g., amino acids)
        # and not useful for searching
        f1 = Q(conditions__conditionset__dataset__in=valid_datasets)
        return self.filter(f1).distinct()

    def all_valid_aliases_list_as_df(self):

        import pandas as pd
        import numpy as np

        conditiontypes = self.all_valid().values("id",
                                                 "name",
                                                 "other_names",
                                                 "pubchem_id",
                                                 "pubchem_name",
                                                 "chebi_id",
                                                 "chebi_name")
        conditiontypes_df = pd.DataFrame(list(conditiontypes))

        # Create a list of aliases
        conditiontypes_df["name_list"] = conditiontypes_df["name"].apply(
            lambda x: [x] if x else [])
        conditiontypes_df["other_names_list"] = conditiontypes_df["other_names"].apply(
            lambda x: x.split("\n") if x else [])
        conditiontypes_df["pubchem_id_list"] = conditiontypes_df["pubchem_id"].apply(
            lambda x: [str(int(x))] if ~np.isnan(x) else [])
        conditiontypes_df["pubchem_name_list"] = conditiontypes_df["pubchem_name"].apply(
            lambda x: [str(x)] if x else [])
        conditiontypes_df["chebi_id_list"] = conditiontypes_df["chebi_id"].apply(
            lambda x: [str(int(x))] if ~np.isnan(x) else [])
        conditiontypes_df["chebi_name_list"] = conditiontypes_df["chebi_name"].apply(
            lambda x: [str(x)] if x else [])

        columns = ["name_list", "other_names_list",
                   "pubchem_id_list", "pubchem_name_list",
                   "chebi_id_list", "chebi_name_list"]
        conditiontypes_df["aliases_list"] = conditiontypes_df[columns].apply(unique_clean_sorted, axis=1)
        conditiontypes_df["aliases_list_as_str"] = conditiontypes_df["aliases_list"].apply(lambda x: "; ".join(x))

        return conditiontypes_df

    def all_valid_tags_list_as_df(self):
        conditiontype_tags = Tag.objects.all_mappings_as_df("conditions", "conditiontype")
        return conditiontype_tags

    def all_valid_as_df(self):

        import pandas as pd

        # Prepare the following fields to be used by Elastic Search:
        # name, aliases_list_as_str, doses_list_as_str, observables_list_as_str
        # papers_list_as_str, tags_list_as_str

        conditiontypes_df = self.all_valid_aliases_list_as_df()

        # Create a list of doses
        conditions = apps.get_model("conditions", "Condition").objects.all_valid().values("id", "type", "dose")
        conditions_df = pd.DataFrame(list(conditions))
        conditiontype_doses = conditions_df.groupby("type").agg({"dose": lambda x: list(x)}).reset_index()
        conditiontype_doses.columns = ["id", "doses_list"]

        conditiontypes_df = conditiontypes_df.merge(conditiontype_doses, how='left', on="id")
        conditiontypes_df["doses_list_as_str"] = conditiontypes_df["doses_list"].apply(lambda x: "; ".join(x))

        # Create a list of tags
        conditiontype_tags = self.all_valid_tags_list_as_df()

        conditiontypes_df = conditiontypes_df.merge(conditiontype_tags, how='left', left_on="id", right_on="id")
        conditiontypes_df.loc[conditiontypes_df['tags_list_as_str'].isnull(), 'tags_list_as_str'] = ""

        # Create list of observables
        with connection.cursor() as cursor:
            cursor.execute("select distinct conditions_conditiontype.id, phenotypes_observable.name \
                           from conditions_conditiontype \
                           inner join conditions_condition \
                                on conditions_conditiontype.id = conditions_condition.type_id \
                           inner join conditions_conditionset_conditions \
                                on conditions_condition.id = conditions_conditionset_conditions.condition_id \
                           inner join conditions_conditionset \
                                on conditions_conditionset_conditions.conditionset_id = conditions_conditionset.id \
                           inner join datasets_dataset \
                                on conditions_conditionset.id = datasets_dataset.conditionset_id \
                           inner join phenotypes_phenotype \
                                on datasets_dataset.phenotype_id = phenotypes_phenotype.id \
                           inner join phenotypes_observable \
                                on phenotypes_phenotype.observable_id = phenotypes_observable.id")
            records = cursor.fetchall()
        t = pd.DataFrame(records, columns=["id", "observable"])
        conditiontype_observables = t.groupby("id").agg(
            {"observable": lambda x: "; ".join(list(x))}).reset_index()
        conditiontype_observables.columns = ["id", "observables_list_as_str"]

        conditiontypes_df = conditiontypes_df.merge(conditiontype_observables, how="left", on="id")

        # Create a list of papers
        valid_paper_ids = apps.get_model("papers", "Paper").objects.all_valid().values_list("id", flat=True)
        valid_paper_ids_list = ", ".join([str(x) for x in valid_paper_ids])
        sql = "select distinct conditions_conditiontype.id, papers_paper.systematic_name \
                           from conditions_conditiontype \
                           inner join conditions_condition \
                                on conditions_conditiontype.id = conditions_condition.type_id \
                           inner join conditions_conditionset_conditions \
                                on conditions_condition.id = conditions_conditionset_conditions.condition_id \
                           inner join conditions_conditionset \
                                on conditions_conditionset_conditions.conditionset_id = conditions_conditionset.id \
                           inner join datasets_dataset \
                                on conditions_conditionset.id = datasets_dataset.conditionset_id \
                           inner join papers_paper \
                                on datasets_dataset.paper_id = papers_paper.id \
                           where papers_paper.id in (%s)" % valid_paper_ids_list
        with connection.cursor() as cursor:
            cursor.execute(sql)
            records = cursor.fetchall()
        t = pd.DataFrame(records, columns=["id", "paper"])
        conditiontype_papers = t.groupby("id").agg(
            {"paper": lambda x: "; ".join(list(x))}).reset_index()
        conditiontype_papers.columns = ["id", "papers_list_as_str"]

        conditiontypes_df = conditiontypes_df.merge(conditiontype_papers, how="left", on="id")

        conditiontypes_df_out = conditiontypes_df[["id",
                                                   "name",
                                                   "aliases_list_as_str",
                                                   "doses_list_as_str",
                                                   "observables_list_as_str",
                                                   "papers_list_as_str",
                                                   "tags_list_as_str"]]

        return conditiontypes_df_out


class ConditionManager(models.Manager):
    def all_valid(self):
        # Valid = associated with at least 1 dataset from a relevant paper
        valid_datasets = apps.get_model("datasets", "Dataset").objects.all_valid()
        f = Q(conditionset__dataset__in=valid_datasets) | Q(
            medium__dataset__in=valid_datasets
        )
        return self.filter(f).distinct()

    def all_valid_aliases_list_as_df(self):

        import pandas as pd

        conditions = self.all_valid().values("id",
                                             "type",
                                             "dose")
        conditions_df = pd.DataFrame(list(conditions))

        conditiontypes_df = apps.get_model("conditions", "ConditionType").objects.all_valid_aliases_list_as_df()
        conditiontypes_df.rename(columns={"aliases_list": "conditiontype_aliases_list"}, inplace=True)

        conditions_df = conditions_df.merge(conditiontypes_df[["id", "name", "conditiontype_aliases_list"]],
                                            how="left", left_on="type", right_on="id")
        conditions_df.rename(columns={"id_x": "id"}, inplace=True)
        conditions_df.drop(columns=["id_y"], inplace=True)

        conditions_df = conditions_df.loc[conditions_df["name"].notnull()]

        def form_display_name(x):
            display_name = [x["name"]]
            if not x["dose"] in ["standard", "unknown"]:
                display_name = [str(x["name"]) + " [" + str(x["dose"]) + "]"]
            return display_name

        conditions_df["display_name"] = conditions_df.apply(form_display_name, axis=1)

        columns = ["display_name", "conditiontype_aliases_list"]
        conditions_df["aliases_list"] = conditions_df[columns].apply(unique_clean_sorted, axis=1)
        conditions_df["aliases_list_as_str"] = conditions_df["aliases_list"].apply(lambda x: "; ".join(x))

        return conditions_df

    def all_valid_tags_list_as_df(self):

        import pandas as pd

        conditions = self.all_valid().values("id", "type")
        conditions_df = pd.DataFrame(list(conditions))

        self_tags = Tag.objects.all_mappings_as_df("conditions", "condition")
        related_tags = apps.get_model("conditions", "ConditionType").objects.all_valid_tags_list_as_df()

        conditions_df = conditions_df.merge(self_tags[["id", "tags_list"]], how="left", on="id")
        conditions_df.rename(columns={"tags_list": "self_tags_list"}, inplace=True)

        conditions_df = conditions_df.merge(related_tags[["id", "tags_list"]], how="left",
                                            left_on="type", right_on="id")
        conditions_df.rename(columns={"id_x": "id", "tags_list": "related_tags_list"}, inplace=True)

        conditions_df["self_tags_list"] = conditions_df["self_tags_list"].apply(
            lambda x: x if isinstance(x, list) else [])
        conditions_df["related_tags_list"] = conditions_df["related_tags_list"].apply(
            lambda x: x if isinstance(x, list) else [])

        conditions_df["tags_list"] = conditions_df["self_tags_list"] + conditions_df["related_tags_list"]
        conditions_df["tags_list"] = conditions_df["tags_list"].apply(lambda x: list(set(x)))

        return conditions_df[["id", "tags_list"]]


class ConditionSetManager(models.Manager):

    def all_valid(self):
        # Valid = associated with at least 1 dataset from a relevant paper
        valid_datasets = apps.get_model("datasets", "Dataset").objects.all_valid()
        return self.filter(dataset__in=valid_datasets).distinct()

    def all_valid_aliases_list_as_df(self):

        import pandas as pd

        conditionsets = self.all_valid().values("id", "systematic_name", "common_name", "display_name")
        conditionsets_df = pd.DataFrame(list(conditionsets))
        conditionsets_df["self_aliases_list"] = \
            conditionsets_df[["systematic_name", "common_name", "display_name"]].values.tolist()

        # Create a list of conditions
        with connection.cursor() as cursor:
            sql = "select distinct conditionset_id, condition_id from conditions_conditionset_conditions"
            cursor.execute(sql)
            records = cursor.fetchall()
        t = pd.DataFrame(records, columns=["id", "condition_id"])

        conditions_df = apps.get_model("conditions", "Condition").objects.all_valid_aliases_list_as_df()
        conditions_df.rename(columns={"aliases_list": "related_aliases_list"}, inplace=True)
        t = t.merge(conditions_df[["id", "related_aliases_list"]], how="left", left_on="condition_id", right_on="id")
        t.rename(columns={'id_x': 'id'}, inplace=True)
        t["related_aliases_list"] = t["related_aliases_list"].apply(lambda x: x if isinstance(x, list) else [])

        conditionset_conditions = t.groupby("id").agg({"related_aliases_list": "sum"}).reset_index()

        conditionsets_df = conditionsets_df.merge(conditionset_conditions[["id", "related_aliases_list"]],
                                                 how="left", on="id")
        columns = ["self_aliases_list", "related_aliases_list"]
        conditionsets_df["aliases_list"] = conditionsets_df[columns].apply(unique_clean_sorted, axis=1)
        conditionsets_df["aliases_list_as_str"] = conditionsets_df["aliases_list"].apply(lambda x: "; ".join(x))

        return conditionsets_df

    def all_valid_tags_list_as_df(self):
        
        import pandas as pd

        self_tags = Tag.objects.all_mappings_as_df("conditions", "conditionset")

        # Create a list of conditions
        with connection.cursor() as cursor:
            sql = "select distinct conditionset_id, condition_id from conditions_conditionset_conditions"
            cursor.execute(sql)
            records = cursor.fetchall()
        t = pd.DataFrame(records, columns=["id", "condition_id"])

        related_tags = apps.get_model("conditions", "Condition").objects.all_valid_tags_list_as_df()
        related_tags.rename(columns={"tags_list": "related_tags_list"}, inplace=True)
        t = t.merge(related_tags[["id", "related_tags_list"]], how="left", left_on="condition_id", right_on="id")
        t.rename(columns={'id_x': 'id'}, inplace=True)
        t["related_tags_list"] = t["related_tags_list"].apply(lambda x: x if isinstance(x, list) else [])

        conditionset_conditions = t.groupby("id").agg({"related_tags_list": "sum"}).reset_index()

        conditionsets_df = self_tags.merge(conditionset_conditions[["id", "related_tags_list"]],
                                           how="outer", on="id")
        conditionsets_df.rename(columns={"tags_list": "self_tags_list"}, inplace=True)
        conditionsets_df["self_tags_list"] = conditionsets_df["self_tags_list"].apply(lambda x:
                                                                                      x if isinstance(x, list) else [])

        columns = ["self_tags_list", "related_tags_list"]
        conditionsets_df["tags_list"] = conditionsets_df[columns].apply(unique_clean_sorted, axis=1)
        conditionsets_df["tags_list_as_str"] = conditionsets_df["tags_list"].apply(lambda x: "; ".join(x))

        return conditionsets_df[["id", "tags_list"]]


class MediumManager(models.Manager):
    def all_valid(self):
        # Valid = associated with at least 1 dataset from a relevant paper
        valid_datasets = apps.get_model("datasets", "Dataset").objects.all_valid()
        return self.filter(dataset__in=valid_datasets).distinct()

    def all_valid_tags_list_as_df(self):

        self_tags = Tag.objects.all_mappings_as_df("conditions", "Medium")

        # # Create a list of conditions
        # with connection.cursor() as cursor:
        #     sql = "select distinct medium_id, condition_id from conditions_medium_conditions"
        #     cursor.execute(sql)
        #     records = cursor.fetchall()
        # t = pd.DataFrame(records, columns=["id", "condition_id"])
        #
        # related_tags = apps.get_model("conditions", "Condition").objects.all_valid_tags_list_as_df()
        # related_tags.rename(columns={"tags_list": "related_tags_list"}, inplace=True)
        # t = t.merge(related_tags[["id", "related_tags_list"]], how="left", left_on="condition_id", right_on="id")
        # t.rename(columns={'id_x': 'id'}, inplace=True)
        # t["related_tags_list"] = t["related_tags_list"].apply(lambda x: x if isinstance(x, list) else [])
        #
        # medium_conditions = t.groupby("id").agg({"related_tags_list": "sum"}).reset_index()
        #
        # mediums_df = self_tags.merge(medium_conditions[["id", "related_tags_list"]],
        #                                    how="outer", on="id")
        mediums_df = self_tags.copy()
        mediums_df.rename(columns={"tags_list": "self_tags_list"}, inplace=True)
        mediums_df["self_tags_list"] = mediums_df["self_tags_list"].apply(lambda x:
                                                                          x if isinstance(x, list) else [])
        # mediums_df["related_tags_list"] = mediums_df["related_tags_list"].apply(lambda x:
        #                                                                         x if isinstance(x, list) else [])

        # columns = ["self_tags_list", "related_tags_list"]
        columns = ["self_tags_list"]
        mediums_df["tags_list"] = mediums_df[columns].apply(unique_clean_sorted, axis=1)
        mediums_df["tags_list_as_str"] = mediums_df["tags_list"].apply(lambda x: "; ".join(x))

        return mediums_df[["id", "tags_list"]]
