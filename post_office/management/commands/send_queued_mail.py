import tempfile
import sys
from optparse import make_option

from django.core.management.base import BaseCommand

from ...lockfile import FileLock, FileLocked
from ...mail import send_queued
from ...logutils import setup_loghandlers


logger = setup_loghandlers()
default_lockfile = tempfile.gettempdir() + "/post_office"


class Command(BaseCommand):

    option_list = BaseCommand.option_list + (
        make_option('-p', '--processes', type='int',
                    help='Number of processes used to send emails', default=1),
        make_option('-L', '--lockfile', type='string', default=default_lockfile,
                    help='Absolute path of lockfile to acquire'),
        make_option('-l', '--log-level', type='int',
                    help='"0" to log nothing, "1" to only log errors'),
    )

    def handle(self, *args, **options):
        logger.info('Acquiring lock for sending queued emails at %s.lock' %
                    options['lockfile'])
        try:
            with FileLock(options['lockfile']):
                try:
                    send_queued(options['processes'], options.get('log_level'))
                except Exception as e:
                    logger.error(e, exc_info=sys.exc_info(), extra={'status_code': 500})
                    raise
        except FileLocked:
            logger.info('Failed to acquire lock, terminating now.')
