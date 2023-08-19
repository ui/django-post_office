from django.core.management.base import BaseCommand

from ...mail import send_queued_mail_until_done


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument(
            '-p', '--processes',
            type=int,
            default=1,
            help='Number of processes used to send emails',
        )
        parser.add_argument(
            '-l', '--log-level',
            type=int,
            help='"0" to log nothing, "1" to only log errors',
        )

    def handle(self, *args, **options):
        send_queued_mail_until_done(options['processes'], options.get('log_level'))
