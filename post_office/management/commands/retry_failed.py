import datetime

from django.core.management.base import BaseCommand
from django.utils.timezone import now

from ...models import Attachment, Email, Log, STATUS


class Command(BaseCommand):
    help = 'Place failed message in queue.'

    def add_arguments(self, parser):
        parser.add_argument('-m', '--max_retries',
                            type=int, default=3,
                            help="specify max retries to put mail in queue")


    def handle(self, verbosity, max_retries, **options):
        # Put failed mail in queue
        email_failed = Email.object.filter(status=STATUS.failed)
        for email in email_failed:
            # Count number of log for retries
            logs_count = Log.object.filter(status=STATUS.failed, email=email).count()
            if logs_count < max_retries:
                email.status = STATUS.queued
                email.save()

