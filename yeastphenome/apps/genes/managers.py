from django.apps import apps
from django.db import models, connection


class GeneManager(models.Manager):

    def all_valid(self):
        return self.all()

    def all_valid_as_df(self):

        import pandas as pd

        # Prepare the following fields to be used by Elastic Search:
        # systematic_name, common_name, aliases_list_as_str, description

        genes = self.all_valid().values("id",
                                        "systematic_name",
                                        "common_name",
                                        "description")
        genes_df = pd.DataFrame(list(genes))

        # Create a list of aliases
        with connection.cursor() as cursor:
            sql = "select distinct gene_id, genealias_id from genes_gene_aliases"
            cursor.execute(sql)
            records = cursor.fetchall()
        t = pd.DataFrame(records, columns=["id", "genealias_id"])

        genealiases_df = apps.get_model("genes", "GeneAlias").objects.all_valid_as_df()
        genealiases_df.rename(columns={"name": "genealias_name"}, inplace=True)
        t = t.merge(genealiases_df, how="left", left_on="genealias_id", right_on="id")
        t.rename(columns={"id_x": "id"}, inplace=True)

        gene_aliases = t.groupby("id").agg({"genealias_name": lambda x: list(x)}).reset_index()
        gene_aliases.columns = ["id", "aliases_list"]

        genes_df = genes_df.merge(gene_aliases, how="left", on="id")
        genes_df.rename(columns={"id_x": "id"}, inplace=True)
        genes_df["aliases_list"] = genes_df["aliases_list"].apply(lambda x: x if isinstance(x, list) else [])
        genes_df["aliases_list_as_str"] = genes_df["aliases_list"].apply(lambda x: "; ".join(x))

        columns = ["id",
                   "systematic_name",
                   "common_name",
                   "aliases_list_as_str",
                   "description"]
        return genes_df[columns]


class GeneAliasManager(models.Manager):

    def all_valid(self):
        return self.all()

    def all_valid_as_df(self):

        import pandas as pd

        genealiases = self.all_valid().values("id", "name")
        genealiases_df = pd.DataFrame(list(genealiases))

        return genealiases_df
