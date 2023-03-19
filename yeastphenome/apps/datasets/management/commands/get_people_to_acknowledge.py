from django.core.management.base import BaseCommand

from yeastphenome.apps.datasets.models import Source


class Command(BaseCommand):
    def handle(self, *args, **options):

        # super(Command, self).handle(*args, **options)

        people = Source.objects.people_to_acknowledge()
        people.sort(key=lambda s: s.split()[1])

        people_str = ', '.join(people)

        self.stdout.write("%s" % people_str)