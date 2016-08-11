import datetime

from django.core.management.base import BaseCommand
from django.utils.timezone import now

from ...models import Email


class Command(BaseCommand):
    help = 'Place deferred messages back in the queue.'

    def add_arguments(self, parser):
        parser.add_argument('-d', '--days',
            type=int,
            default=90,
            help="Cleanup mails older than this many days, defaults to 90."
            )

    def handle(self, verbosity, days, **options):
        # Delete mails and their related logs and queued created before X days

        cutoff_date = now() - datetime.timedelta(days)
        count = Email.objects.filter(created__lt=cutoff_date).count()
        Email.objects.only('id').filter(created__lt=cutoff_date).delete()
        print("Deleted {0} mails created before {1} ".format(count, cutoff_date))
