from django.core.management.base import BaseCommand

from ...utils import send_all


class Command(BaseCommand):

     def handle(self, *args, **options):
        send_queued_mails()