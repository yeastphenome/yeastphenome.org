from django.core.management.base import BaseCommand
from django.db.models import Q, Count
from django.db.models.functions import Concat
from django.apps import apps

import time

from yeastphenome.apps.genes.models import Gene


class Command(BaseCommand):
    def handle(self, *args, **options):

        obj = Gene.objects.get(pk=3950)

        # Option 1
        start_time = time.time()
        ps = obj.get_data()
        duration = time.time() - start_time
        self.stdout.write("Option 1: %.3f." % duration)

        # option 2
        start_time = time.time()
        ps = obj.data_set.values_list("dataset", "dataset__name", "valuez")
        duration = time.time() - start_time
        self.stdout.write("Option 2: %.3f." % duration)

        # # Option 1
        # start_time = time.time()
        # ps = apps.get_model("conditions", "Condition")\
        #     .objects.all_valid().filter(type=obj)\
        #     .distinct()\
        #     .order_by("dose")
        # ps_list_str = "; ".join([(u"%s" % p) for p in ps])
        # duration = time.time() - start_time
        # self.stdout.write("Option 1: %.3f." % duration)
        #
        # # Option 2
        # start_time = time.time()
        # ps = list(set(obj.conditions.all_valid().values_list("dose", flat=True)))
        # ps = sorted(ps)
        # ps_list_str = "; ".join(ps)
        # duration = time.time() - start_time
        # self.stdout.write("Option 2: %3f." % duration)
        #
        # # Option 3
        # start_time = time.time()
        # ps = obj.conditions.all_valid().values_list("dose", flat=True).order_by().distinct()
        # ps_list_str = "; ".join(ps)
        # duration = time.time() - start_time
        # self.stdout.write("Option 3: %3f." % duration)

