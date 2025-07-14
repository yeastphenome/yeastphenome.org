from django.apps import apps
from django.db import models, connection
from django.db.models import Q


class TagManager(models.Manager):

    def all_valid(self, **kwargs):
        obj = self.all()
        if "type" in kwargs:
            if kwargs["type"] == "conditions":
                valid_conditiontypes = apps.get_model(
                    "conditions", "Conditiontype"
                ).objects.all_valid()
                valid_conditions = apps.get_model(
                    "conditions", "Condition"
                ).objects.all_valid()
                obj = obj.filter(
                    Q(condition__in=valid_conditions)
                    | Q(conditiontype__in=valid_conditiontypes)
                ).distinct()
            elif kwargs["type"] == "datasets":
                valid_datasets = apps.get_model(
                    "datasets", "Dataset"
                ).objects.all_valid()
                obj = obj.filter(dataset__in=valid_datasets)
            elif kwargs["type"] == "phenotypes":
                valid_observables = apps.get_model(
                    "phenotypes", "Observable"
                ).objects.all_valid()
                obj = obj.filter(observables__in=valid_observables)
        return obj

    def all_as_df(self):
        
        import pandas as pd

        tags = self.all().values("id", "name")
        tags_df = pd.DataFrame(list(tags))
        return tags_df

    def all_mappings_as_df(self, app, model):

        import pandas as pd

        tags_df = self.all_as_df()

        table = "_".join([app, model, "tags"])

        with connection.cursor() as cursor:
            cursor.execute("SELECT * from %s" % table)
            records = cursor.fetchall()

        if records:
            t = pd.DataFrame(records, columns = ["id", model, "tag"])
            t = t.merge(tags_df, how="left", left_on="tag", right_on="id")

            model_tags = t.groupby(model).agg({"name": lambda x: sorted(list(x))}).reset_index()
            model_tags.columns = ["id", "tags_list"]
            model_tags["tags_list_as_str"] = model_tags["tags_list"].apply(lambda x: "; ".join(x))
        else:
            model_tags = pd.DataFrame(columns=["id", "tags_list", "tags_list_as_str"])
        return model_tags
