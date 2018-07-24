from django.core.management.base import BaseCommand

from ...models import Email


class Command(BaseCommand):
    help = 'Suspend queued email sending.'

    def handle(self, **options):
        Email.suspend()
