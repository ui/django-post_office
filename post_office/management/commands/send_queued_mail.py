import tempfile
from optparse import make_option

from django.core.management.base import BaseCommand

from ...lockfile import FileLock
from ...mail import send_queued


class Command(BaseCommand):

    option_list = BaseCommand.option_list + (
        make_option('-p', '--processes', type='int',
                    help='Number of processes used to send emails', default=1),
    )

    def handle(self, *args, **options):
        with FileLock(tempfile.gettempdir() + "/post_office", timeout=1):
            send_queued(options['processes'])
