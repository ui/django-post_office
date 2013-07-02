import tempfile

from django.core.management.base import BaseCommand

from ...lockfile import FileLock
from ..utils import send_queued


class Command(BaseCommand):

    def handle(self, *args, **options):
        with FileLock(tempfile.gettempdir() + "/post_office", timeout=1):
            send_queued()
