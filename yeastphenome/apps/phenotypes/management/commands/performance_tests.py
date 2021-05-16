from django.core.management.base import BaseCommand
from django.db.models import Q, Count
from django.db.models.functions import Concat
from django.apps import apps

import time

from yeastphenome.apps.phenotypes.models import Observable


class Command(BaseCommand):
    def handle(self, *args, **options):

        growth_obj = Observable.objects.get(pk=2)

        # Option 1
        start_time = time.time()
        ps = apps.get_model("papers", "Paper")\
            .objects.all_valid().filter(datasets__phenotype__observable=growth_obj)\
            .distinct()\
            .order_by("first_author")
        ps_list_str = "; ".join([(u"%s" % p) for p in ps])
        duration = time.time() - start_time
        self.stdout.write("Option 1: %.3f." % duration)

        # Option 2
        start_time = time.time()
        ps = list(set(growth_obj.phenotype_set.all_valid().values_list("dataset__paper__systematic_name", flat=True)))
        ps = sorted(ps)
        ps_list_str = "; ".join(ps)
        duration = time.time() - start_time
        self.stdout.write("Option 2: %3f." % duration)

        # Option 3
        start_time = time.time()
        ps = growth_obj.phenotype_set.all_valid().values_list("dataset__paper__systematic_name", flat=True).order_by().distinct()
        ps_list_str = "; ".join(ps)
        duration = time.time() - start_time
        self.stdout.write("Option 3: %3f." % duration)

