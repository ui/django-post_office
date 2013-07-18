import tempfile
import sys
from optparse import make_option

from django.core.management.base import BaseCommand

from ...lockfile import FileLock
from ...mail import send_queued
from ...logutils import setup_loghandlers


logger = setup_loghandlers()


class Command(BaseCommand):

    option_list = BaseCommand.option_list + (
        make_option('-p', '--processes', type='int',
                    help='Number of processes used to send emails', default=1),
    )

    def handle(self, *args, **options):
        with FileLock(tempfile.gettempdir() + "/post_office", timeout=1):
            try:
                send_queued(options['processes'])
            except Exception, e:
                logger.error(e, exc_info=sys.exc_info(), extra={'status_code': 500})
                raise
