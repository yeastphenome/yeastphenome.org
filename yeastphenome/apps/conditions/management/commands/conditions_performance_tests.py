from django.core.management.base import BaseCommand

import time

from yeastphenome.apps.conditions.models import ConditionType


class Command(BaseCommand):
    def handle(self, *args, **options):

        obj = ConditionType.objects.get(pk=2)

        # Option 1
        start_time = time.time()
        _ = obj.papers()
        duration = time.time() - start_time
        self.stdout.write("Option 1: %.3f." % duration)

        # option 2
        start_time = time.time()
        _ = obj.papers2()
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
