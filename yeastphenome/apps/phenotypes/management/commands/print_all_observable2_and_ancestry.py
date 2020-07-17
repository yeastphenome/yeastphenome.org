from django.core.management.base import BaseCommand

from phenotypes.models import Observable2


class Command(BaseCommand):
    def handle(self, *args, **options):

        observable2_qs = Observable2.objects.all()

        for observable2 in observable2_qs:
            self.stdout.write(
                "%s\t%s\t%s"
                % (observable2.ancestry, observable2, observable2.get_ancestry_names())
            )
