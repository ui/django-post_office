import datetime

from django.core.management import call_command
from django.test import TestCase

from ..models import Email

try:
    from django.utils.timezone import now
    now = now
except ImportError:
    now = datetime.now


class CommandTest(TestCase):

    def test_cleanup_mail(self):
        """
        The ``cleanup_mail`` command deletes mails older than a specified
        amount of days
        """
        self.assertEqual(Email.objects.count(), 0)

        # The command shouldn't delete today's email
        email = Email.objects.create(from_email='from@example.com', to='to@example.com')
        call_command('cleanup_mail', days=30)
        self.assertEqual(Email.objects.count(), 1)

        # Email older than 30 days should be deleted
        email.created = now() - datetime.timedelta(31)
        email.save()
        call_command('cleanup_mail', days=30)
        self.assertEqual(Email.objects.count(), 0)
