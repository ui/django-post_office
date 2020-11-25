from django.core.management.base import BaseCommand

from ...lockfile import default_lockfile
from ...mail import send_all_in_queue
from ...logutils import setup_loghandlers


logger = setup_loghandlers()


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument(
            '-p', '--processes',
            type=int,
            default=1,
            help='Number of processes used to send emails',
        )
        parser.add_argument(
            '-L', '--lockfile',
            default=default_lockfile,
            help='Absolute path of lockfile to acquire',
        )
        parser.add_argument(
            '-l', '--log-level',
            type=int,
            help='"0" to log nothing, "1" to only log errors',
        )

    def handle(self, *args, **options):
        logger.info('Acquiring lock for sending queued emails at %s.lock', options['lockfile'])
        send_all_in_queue(options['lockfile'], options['processes'], options.get('log_level'))
