from django.apps import apps
from django.db import models, connection
from django.db.models import Q

from yeastphenome.apps.tags.models import Tag


class ObservableManager(models.Manager):

    def all_valid(self):
        valid_datasets = apps.get_model("datasets", "Dataset").objects.all_valid()
        f = Q(phenotype__dataset__in=valid_datasets)
        return self.filter(f).distinct()

    def all_valid_as_df(self):

        import pandas as pd
        import numpy as np

        # Prepare the following fields to be used by Elastic Search:
        # name, description, phenotypes_list_as_str, reporters_list_as_str,
        # conditiontypes_list_as_str, papers_list_as_str,
        # tags_list_as_str

        observables = self.all_valid().values("id", "name", "description")
        observables_df = pd.DataFrame(list(observables))
        observables_df.loc[observables_df["description"].isnull(), "description"] = ""

        # Get list of related phenotypes
        phenotypes = apps.get_model("phenotypes", "Phenotype").objects.all_valid().values("id",
                                                                                          "name",
                                                                                          "observable",
                                                                                          "reporter")
        phenotypes_df = pd.DataFrame(list(phenotypes))

        observable2phenotypes = phenotypes_df.groupby("observable").agg({"name": lambda x: list(x),
                                                                         "reporter": lambda x: list(x)}).reset_index()
        observable2phenotypes.columns = ["id", "phenotypes_list", "reporters_list"]

        remove_list = ["undefined", "none", "", None, np.nan, "nan", "NaN", "unknown"]
        observable2phenotypes["reporters_list"] = \
            observable2phenotypes["reporters_list"].apply(lambda x: [xi for xi in x if xi not in remove_list])

        observables_df = observables_df.merge(observable2phenotypes, how="left", on="id")
        observables_df["phenotypes_list"] = \
            observables_df["phenotypes_list"].apply(lambda x: x if isinstance(x, list) else [])
        observables_df["phenotypes_list_as_str"] = observables_df["phenotypes_list"].apply(lambda x: "; ".join(x))
        observables_df["reporters_list"] = \
            observables_df["reporters_list"].apply(lambda x: x if isinstance(x, list) else [])
        observables_df["reporters_list_as_str"] = observables_df["reporters_list"].apply(lambda x: "; ".join(x))

        # Get list of related conditiontypes
        sql = "select distinct phenotypes_observable.id, conditions_conditiontype.name from phenotypes_observable \
                inner join phenotypes_phenotype on phenotypes_observable.id = phenotypes_phenotype.observable_id \
                inner join datasets_dataset on phenotypes_phenotype.id = datasets_dataset.phenotype_id \
                inner join conditions_conditionset on datasets_dataset.conditionset_id = conditions_conditionset.id \
                inner join conditions_conditionset_conditions on conditions_Conditionset.id = conditions_conditionset_conditions.conditionset_id \
                inner join conditions_condition on conditions_conditionset_conditions.condition_id = conditions_condition.id \
                inner join conditions_conditiontype on conditions_condition.type_id = conditions_conditiontype.id"
        with connection.cursor() as cursor:
            cursor.execute(sql)
            records = cursor.fetchall()
        t = pd.DataFrame(records, columns=["id", "conditiontype"])
        observable2conditiontypes = t.groupby("id").agg({"conditiontype": lambda x: list(x)}).reset_index()
        observable2conditiontypes.columns = ["id", "conditiontypes_list"]

        observables_df = observables_df.merge(observable2conditiontypes, how="left", on="id")
        observables_df["conditiontypes_list"] = \
            observables_df["conditiontypes_list"].apply(lambda x: x if isinstance(x, list) else [])
        observables_df["conditiontypes_list_as_str"] = observables_df["conditiontypes_list"].apply(lambda x: "; ".join(x))

        # Get list of related papers
        sql = "select distinct phenotypes_observable.id, papers_paper.systematic_name from phenotypes_observable \
                inner join phenotypes_phenotype on phenotypes_observable.id = phenotypes_phenotype.observable_id \
                inner join datasets_dataset on phenotypes_phenotype.id = datasets_dataset.phenotype_id \
                inner join papers_paper on datasets_dataset.paper_id = papers_paper.id"
        with connection.cursor() as cursor:
            cursor.execute(sql)
            records = cursor.fetchall()
        t = pd.DataFrame(records, columns=["id", "paper"])
        observable2papers = t.groupby("id").agg({"paper": lambda x: list(x)}).reset_index()
        observable2papers.columns = ["id", "papers_list"]

        observables_df = observables_df.merge(observable2papers, how="left", on="id")
        observables_df["papers_list"] = \
            observables_df["papers_list"].apply(lambda x: x if isinstance(x, list) else [])
        observables_df["papers_list_as_str"] = observables_df["papers_list"].apply(lambda x: "; ".join(x))

        # Get list of tags
        tags = Tag.objects.all_mappings_as_df("phenotypes", "observable")
        observables_df = observables_df.merge(tags[["id", "tags_list_as_str"]], how="left", on="id")
        observables_df.loc[observables_df["tags_list_as_str"].isnull(), "tags_list_as_str"] = ""

        columns = ["id",
                   "name",
                   "description",
                   "phenotypes_list_as_str",
                   "reporters_list_as_str",
                   "conditiontypes_list_as_str",
                   "papers_list_as_str",
                   "tags_list_as_str"]
        return observables_df[columns]


class PhenotypeManager(models.Manager):

    def all_valid(self):
        # Valid = is associated with >=1 valid dataset
        valid_phenotypes = apps.get_model("datasets", "Dataset").objects.all_valid().values("phenotype").distinct()
        return self.filter(pk__in=valid_phenotypes)

    def all_valid_aliases_list_as_df(self):

        import pandas as pd

        phenotypes = self.all_valid().values("id", "name", "observable__name", "reporter")
        phenotypes_df = pd.DataFrame(list(phenotypes))

        def form_display_name(x):
            display_name = x["observable__name"]
            if x["reporter"]:
                display_name = str(x["observable__name"]) + " (" + str(x["reporter"]) + ")"
            return display_name

        phenotypes_df["display_name"] = phenotypes_df.apply(form_display_name, axis=1)

        phenotypes_df["aliases_list"] = \
            phenotypes_df[["name", "display_name", "observable__name"]].values.tolist()

        phenotypes_df["aliases_list"] = phenotypes_df["aliases_list"].apply(lambda x: list(set(x)))
        phenotypes_df["aliases_list_as_str"] = phenotypes_df["aliases_list"].apply(lambda x: "; ".join(x))

        return phenotypes_df

    def all_valid_tags_list_as_df(self):

        import pandas as pd

        phenotypes = self.all_valid().values("id", "observable")
        phenotypes_df = pd.DataFrame(list(phenotypes))

        self_tags = Tag.objects.all_mappings_as_df("phenotypes", "Phenotype")
        related_tags = Tag.objects.all_mappings_as_df("phenotypes", "Observable")

        phenotypes_df = phenotypes_df.merge(self_tags[["id", "tags_list"]], how="left", on="id")
        phenotypes_df.rename(columns={"id_x": "id",
                                      "tags_list": "self_tags_list"}, inplace=True)

        phenotypes_df = phenotypes_df.merge(related_tags[["id", "tags_list"]], how="left",
                                            left_on="observable", right_on="id")
        phenotypes_df.rename(columns={"id_x": "id",
                                      "tags_list": "related_tags_list"}, inplace=True)

        phenotypes_df["self_tags_list"] = phenotypes_df["self_tags_list"].apply(
            lambda x: x if isinstance(x, list) else [])
        phenotypes_df["related_tags_list"] = phenotypes_df["related_tags_list"].apply(
            lambda x: x if isinstance(x, list) else [])

        phenotypes_df["tags_list"] = phenotypes_df["self_tags_list"] + phenotypes_df["related_tags_list"]
        phenotypes_df["tags_list"] = phenotypes_df["tags_list"].apply(lambda x: list(set(x)))

        return phenotypes_df[["id", "tags_list"]]
